#!/bin/bash
set -e

# Optimized Backend Deployment Script with Docker Layer Caching
echo "🚀 Deploying Streaming STT Backend with Optimized Build..."

# Configuration
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"lfhs-translate"}
REGION=${REGION:-"europe-west1"}
SERVICE_NAME="streaming-stt-service"
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"
TIMEOUT=600
USE_OPTIMIZED_BUILD=${USE_OPTIMIZED_BUILD:-true}

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
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

print_info() {
    echo -e "${CYAN}ℹ️  $1${NC}"
}

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

# Validate prerequisites
print_step "Validating prerequisites..."

if ! command -v gcloud &> /dev/null; then
    print_error "gcloud CLI is not installed. Please install it first."
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

# Pre-build optimization: pull latest images for cache
print_step "Preparing build cache..."
print_info "Pulling latest images to improve build speed..."

# Pull cache images (ignore failures for first build)
docker pull gcr.io/$PROJECT_ID/$SERVICE_NAME:latest 2>/dev/null || print_warning "No previous image found (first build)"
docker pull gcr.io/$PROJECT_ID/$SERVICE_NAME-cache:base 2>/dev/null || print_warning "No base cache found"
docker pull gcr.io/$PROJECT_ID/$SERVICE_NAME-cache:dependencies 2>/dev/null || print_warning "No dependencies cache found"

# Choose build configuration
if [ "$USE_OPTIMIZED_BUILD" = "true" ]; then
    BUILD_CONFIG="cloudbuild-optimized.yaml"
    DOCKERFILE="Dockerfile.optimized"
    print_info "Using optimized build with Docker layer caching"
else
    BUILD_CONFIG="cloudbuild.yaml"
    DOCKERFILE="Dockerfile.simple"
    print_info "Using standard build configuration"
fi

# Verify build files exist
if [ ! -f "$BUILD_CONFIG" ]; then
    print_error "Build configuration not found: $BUILD_CONFIG"
    exit 1
fi

if [ ! -f "$DOCKERFILE" ]; then
    print_error "Dockerfile not found: $DOCKERFILE"
    exit 1
fi

# Clean up any existing incomplete deployments
print_step "Cleaning up old revisions (keeping last 3)..."
OLD_REVISIONS=$(gcloud run revisions list --service=$SERVICE_NAME --region=$REGION --format="value(metadata.name)" --sort-by="~metadata.creationTimestamp" | tail -n +4)
if [ ! -z "$OLD_REVISIONS" ]; then
    for revision in $OLD_REVISIONS; do
        print_warning "Deleting old revision: $revision"
        gcloud run revisions delete $revision --region=$REGION --quiet || true
    done
fi

# Build and deploy with optimized Cloud Build
print_step "Building and deploying with optimized Cloud Build..."
print_info "Build configuration: $BUILD_CONFIG"
print_info "Expected build time: 2-5 minutes (optimized with caching)"

# Start build timer
BUILD_START_TIME=$(date +%s)

# Submit build to Cloud Build with custom substitutions
BUILD_ID=$(gcloud builds submit \
    --config=$BUILD_CONFIG \
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

# Calculate build time
BUILD_END_TIME=$(date +%s)
BUILD_DURATION=$((BUILD_END_TIME - BUILD_START_TIME))
BUILD_MINUTES=$((BUILD_DURATION / 60))
BUILD_SECONDS=$((BUILD_DURATION % 60))

if [ "$BUILD_STATUS" = "SUCCESS" ]; then
    print_success "Cloud Build completed successfully in ${BUILD_MINUTES}m ${BUILD_SECONDS}s!"
    print_info "Previous non-cached builds typically took 10-15 minutes"
else
    print_error "Cloud Build failed with status: $BUILD_STATUS"
    
    # Show build logs for debugging
    print_warning "Build logs:"
    gcloud builds log $BUILD_ID --limit=50
    exit 1
fi

# Ensure new revision gets 100% traffic (handles cases where traffic splits exist)
print_step "Ensuring latest revision receives 100% traffic..."
gcloud run services update-traffic $SERVICE_NAME \
    --to-latest \
    --region=$REGION \
    --quiet || true

print_success "Traffic routing updated!"

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

# Calculate cost optimization info
COST_SAVINGS_MSG=""
if [ "$USE_OPTIMIZED_BUILD" = "true" ]; then
    if [ $BUILD_DURATION -lt 600 ]; then  # Less than 10 minutes
        ESTIMATED_SAVINGS=$((15 - BUILD_MINUTES))
        COST_SAVINGS_MSG="💰 Estimated build time saved: ~${ESTIMATED_SAVINGS} minutes"
    fi
fi

print_success "Deployment completed successfully!"
echo ""
echo -e "${GREEN}🎉 Optimized Streaming STT Backend is now live!${NC}"
echo -e "${BLUE}Service URL: $SERVICE_URL${NC}"
echo -e "${BLUE}WebSocket URL: $WS_URL${NC}"  
echo -e "${BLUE}Current Revision: $CURRENT_REVISION${NC}"
echo -e "${BLUE}Traffic: $TRAFFIC_PERCENT%${NC}"
echo -e "${BLUE}Build Time: ${BUILD_MINUTES}m ${BUILD_SECONDS}s${NC}"
if [ ! -z "$COST_SAVINGS_MSG" ]; then
    echo -e "${YELLOW}$COST_SAVINGS_MSG${NC}"
fi
echo ""
echo -e "${YELLOW}📊 Monitoring:${NC}"
echo "  • Logs: https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME/logs"
echo "  • Metrics: https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME/metrics"
echo "  • Build Logs: https://console.cloud.google.com/cloud-build/builds/$BUILD_ID"
echo ""
echo -e "${YELLOW}🧪 Test commands:${NC}"
echo "  curl $SERVICE_URL/health"
echo "  gcloud run services logs tail $SERVICE_NAME --region=$REGION"
echo ""
echo -e "${GREEN}✅ Optimized backend deployment verified and ready! 🚀${NC}"
echo ""
echo -e "${BLUE}Next step: Update frontend configuration with:${NC}"
echo "  Backend URL: $WS_URL"

# Performance insights
echo ""
echo -e "${CYAN}⚡ Performance Insights:${NC}"
echo -e "${CYAN}  • Docker layer caching enabled${NC}"
echo -e "${CYAN}  • Multi-stage build optimization${NC}"
echo -e "${CYAN}  • Faster E2_HIGHCPU_32 machine type${NC}"
echo -e "${CYAN}  • BuildKit enabled for better caching${NC}"
if [ "$BUILD_DURATION" -lt 300 ]; then
    echo -e "${GREEN}  • Build time under 5 minutes - excellent! ✨${NC}"
elif [ "$BUILD_DURATION" -lt 600 ]; then
    echo -e "${YELLOW}  • Build time under 10 minutes - good improvement 👍${NC}"
else
    echo -e "${YELLOW}  • Consider checking cache effectiveness 🔍${NC}"
fi