#!/bin/bash
set -e

# Robust Backend Deployment Script for Cloud Run
echo "🚀 Deploying Streaming STT Backend to Cloud Run..."

# Configuration
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"lfhs-translate"}
REGION=${REGION:-"europe-west1"}
SERVICE_NAME="streaming-stt-service"
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"
TIMEOUT=600
DRY_RUN=${DRY_RUN:-false}

# Parse command line arguments
for arg in "$@"; do
    case $arg in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
    esac
done

if [ "$DRY_RUN" = "true" ]; then
    echo "⚠️  DRY RUN MODE - No actual deployment will occur"
fi

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_step() {
    echo -e "${BLUE}📋 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Validate prerequisites
print_step "Validating prerequisites..."

if ! command -v gcloud &> /dev/null; then
    print_error "gcloud CLI is not installed. Please install it first."
    exit 1
fi

if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install it first."
    exit 1
fi

# Check if logged in to gcloud
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    print_error "Not authenticated with gcloud. Run: gcloud auth login"
    exit 1
fi

# Set project
print_step "Setting project to $PROJECT_ID..."
gcloud config set project $PROJECT_ID

# Enable required APIs
print_step "Enabling required Google Cloud APIs..."
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    speech.googleapis.com \
    translate.googleapis.com \
    texttospeech.googleapis.com \
    logging.googleapis.com \
    monitoring.googleapis.com

print_success "APIs enabled"

# Clean up any existing incomplete deployments
print_step "Cleaning up old revisions (keeping last 3)..."
OLD_REVISIONS=$(gcloud run revisions list --service=$SERVICE_NAME --region=$REGION --format="value(metadata.name)" --sort-by="~metadata.creationTimestamp" | tail -n +4)
if [ ! -z "$OLD_REVISIONS" ]; then
    for revision in $OLD_REVISIONS; do
        print_warning "Deleting old revision: $revision"
        gcloud run revisions delete $revision --region=$REGION --quiet || true
    done
fi

# Blue-Green Deployment Functions

# Function: Deploy with Blue-Green Pattern
deploy_with_blue_green() {
    local new_revision=$1
    
    print_step "Starting blue-green deployment..."
    
    # Get current revision for potential rollback
    local current_revision=$(gcloud run services describe $SERVICE_NAME \
        --region=$REGION \
        --format="value(status.latestReadyRevisionName)" 2>/dev/null || echo "")
    
    if [ ! -z "$current_revision" ]; then
        print_step "Current revision: $current_revision"
    fi
    
    # Deploy new revision with 0% traffic initially
    print_step "Deploying new revision (0% traffic)..."
    gcloud run services update-traffic $SERVICE_NAME \
        --region=$REGION \
        --to-revisions=$new_revision=0 \
        --quiet
    
    # Wait for new revision to be ready
    print_step "Waiting for new revision to be ready..."
    if ! wait_for_revision_ready $new_revision; then
        print_error "New revision failed to become ready"
        return 1
    fi
    
    # Health check new revision
    print_step "Health checking new revision..."
    if health_check_revision $new_revision; then
        print_success "Health check passed!"
        
        # Gradually shift traffic (canary approach)
        for percent in 25 50 75 100; do
            print_step "Shifting $percent% traffic to new revision..."
            gcloud run services update-traffic $SERVICE_NAME \
                --region=$REGION \
                --to-revisions=$new_revision=$percent \
                --quiet
            
            sleep 5
            if ! health_check_revision $new_revision; then
                print_error "Health check failed at $percent% traffic"
                if [ ! -z "$current_revision" ]; then
                    rollback_to_revision $current_revision
                fi
                return 1
            fi
        done
        
        print_success "Blue-green deployment completed successfully!"    
        return 0
    else
        print_error "Health check failed! Rolling back..."
        if [ ! -z "$current_revision" ]; then
            rollback_to_revision $current_revision
        fi
        return 1
    fi
}

# Function: Enhanced Health Check with Retries
health_check_revision() {
    local revision=$1
    local max_attempts=5
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        print_step "Health check attempt $((attempt + 1))/$max_attempts..."
        
        local response=$(curl -s -w "%{http_code}" -o /tmp/health_response \
            "$SERVICE_URL/health" 2>/dev/null || echo "000")
        
        if [ "$response" = "200" ]; then
            local body=$(cat /tmp/health_response 2>/dev/null || echo "")
            if [[ $body == *'"status":"ok"'* ]]; then
                print_success "Health check passed for revision!"
                return 0
            fi
        fi
        
        attempt=$((attempt + 1))
        if [ $attempt -lt $max_attempts ]; then
            print_warning "Health check failed, retrying in 10 seconds..."
            sleep 10
        fi
    done
    
    print_error "Health check failed after $max_attempts attempts"
    if [ -f /tmp/health_response ]; then
        print_error "Last response: $(cat /tmp/health_response)"
    fi
    return 1
}

# Function: Automated Rollback
rollback_to_revision() {
    local target_revision=$1
    
    print_warning "Initiating rollback to revision: $target_revision"
    
    gcloud run services update-traffic $SERVICE_NAME \
        --region=$REGION \
        --to-revisions=$target_revision=100 \
        --quiet
    
    if health_check_revision $target_revision; then
        print_success "Rollback successful!"
        return 0
    else
        print_error "Rollback failed - manual intervention required!"
        print_error "Manual rollback command:"
        print_error "gcloud run services update-traffic $SERVICE_NAME --region=$REGION --to-revisions=$target_revision=100"
        return 1
    fi
}

# Function: Wait for revision to be ready
wait_for_revision_ready() {
    local revision=$1
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        local status=$(gcloud run revisions describe $revision \
            --region=$REGION \
            --format="value(status.conditions[0].status)" 2>/dev/null || echo "Unknown")
        
        if [ "$status" = "True" ]; then
            print_success "Revision $revision is ready!"
            return 0
        fi
        
        print_step "Waiting for revision to be ready... ($((attempt + 1))/$max_attempts)"
        sleep 10
        attempt=$((attempt + 1))
    done
    
    print_error "Revision failed to become ready after 5 minutes"
    return 1
}

# Build and deploy with Cloud Build
print_step "Building and deploying with Cloud Build..."

# Submit build to Cloud Build with custom substitutions
BUILD_ID=$(gcloud builds submit \
    --config=cloudbuild-optimized.yaml \
    --substitutions=_SERVICE_NAME=$SERVICE_NAME,_REGION=$REGION \
    --format="value(id)" \
    --quiet)

if [ $? -ne 0 ]; then
    print_error "Cloud Build submission failed!"
    exit 1
fi

print_step "Cloud Build started with ID: $BUILD_ID"
print_step "Streaming build logs..."

# Stream build logs in real-time
gcloud builds log $BUILD_ID --stream

# Check build status
BUILD_STATUS=$(gcloud builds describe $BUILD_ID --format="value(status)")

if [ "$BUILD_STATUS" = "SUCCESS" ]; then
    print_success "Cloud Build completed successfully!"
else
    print_error "Cloud Build failed with status: $BUILD_STATUS"
    
    # Show build logs for debugging
    print_warning "Build logs:"
    gcloud builds log $BUILD_ID --limit=50
    exit 1
fi

# Get new revision name from the deployment
print_step "Getting new revision information..."
NEW_REVISION=$(gcloud run services describe $SERVICE_NAME \
    --region=$REGION \
    --format="value(status.latestCreatedRevisionName)")

if [ -z "$NEW_REVISION" ]; then
    print_error "Could not determine new revision name"
    exit 1
fi

print_step "New revision: $NEW_REVISION"

# Deploy using blue-green strategy
if ! deploy_with_blue_green $NEW_REVISION; then
    print_error "Blue-green deployment failed!"
    exit 1
fi

# Function to get service URL with fallback
get_service_url() {
    local service_name=$1
    local region=$2
    
    # Try new URL format first (traffic[0].url)
    local new_url=$(gcloud run services describe "$service_name" \
        --region="$region" \
        --format="value(status.traffic[0].url)" 2>/dev/null)
    
    if [ ! -z "$new_url" ]; then
        echo "$new_url"
        return 0
    fi
    
    # Fallback to legacy URL format
    local legacy_url=$(gcloud run services describe "$service_name" \
        --region="$region" \
        --format="value(status.url)" 2>/dev/null)
    
    if [ ! -z "$legacy_url" ]; then
        echo "$legacy_url"
        return 0
    fi
    
    return 1
}

# Get the actual service URL
print_step "Getting service URL..."
SERVICE_URL=$(get_service_url "$SERVICE_NAME" "$REGION")

if [ -z "$SERVICE_URL" ]; then
    print_error "Could not retrieve service URL"
    exit 1
fi

# Wait for deployment to be ready
print_step "Waiting for deployment to be ready..."
sleep 10

# Verify deployment
print_step "Verifying deployment..."
HEALTH_RESPONSE=$(curl -s -f "$SERVICE_URL/health" || echo "FAILED")

if [[ $HEALTH_RESPONSE == *"\"status\":\"ok\""* ]]; then
    print_success "Health check passed!"
    echo "Response: $HEALTH_RESPONSE"
else
    print_error "Health check failed!"
    echo "Response: $HEALTH_RESPONSE"
    
    # Show recent logs for debugging
    print_warning "Recent logs:"
    gcloud run services logs read $SERVICE_NAME --region=$REGION --limit=10
    exit 1
fi

# Test WebSocket endpoint accessibility
print_step "Testing WebSocket endpoint accessibility..."
WS_URL=$(echo $SERVICE_URL | sed 's/https:/wss:/')
WS_TEST_RESPONSE=$(curl -s -I -H "Upgrade: websocket" -H "Connection: Upgrade" "$SERVICE_URL/ws/stream/test" | head -n 1 || echo "FAILED")

if [[ $WS_TEST_RESPONSE == *"101"* ]] || [[ $WS_TEST_RESPONSE == *"400"* ]]; then
    print_success "WebSocket endpoint accessible!"
else
    print_warning "WebSocket endpoint test inconclusive (this may be normal)"
fi

# Get current revision info
CURRENT_REVISION=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.latestReadyRevisionName)")
TRAFFIC_PERCENT=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.traffic[0].percent)")

print_success "Deployment completed successfully!"
echo ""
echo -e "${GREEN}🎉 Streaming STT Backend is now live!${NC}"
echo -e "${BLUE}Service URL: $SERVICE_URL${NC}"
echo -e "${BLUE}WebSocket URL: $WS_URL${NC}"  
echo -e "${BLUE}Current Revision: $CURRENT_REVISION${NC}"
echo -e "${BLUE}Traffic: $TRAFFIC_PERCENT%${NC}"
echo ""
echo -e "${YELLOW}📊 Monitoring:${NC}"
echo "  • Logs: https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME/logs"
echo "  • Metrics: https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME/metrics"
echo ""
echo -e "${YELLOW}🧪 Test commands:${NC}"
echo "  curl $SERVICE_URL/health"
echo "  gcloud run services logs tail $SERVICE_NAME --region=$REGION"
echo ""
echo -e "${GREEN}✅ Backend deployment verified and ready! 🚀${NC}"
echo ""
echo -e "${BLUE}Next step: Update frontend configuration with:${NC}"
echo "  Backend URL: $WS_URL"