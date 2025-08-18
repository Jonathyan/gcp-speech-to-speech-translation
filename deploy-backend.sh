#!/bin/bash
set -e

# Robust Backend Deployment Script for Cloud Run
echo "🚀 Deploying Streaming STT Backend to Cloud Run..."

# Configuration
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"lfhs-translate"}
REGION=${REGION:-"europe-west1"}
SERVICE_NAME="streaming-stt-service"
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"
TIMEOUT=300

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

# Build and push Docker image
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
NEW_IMAGE="$IMAGE_NAME:$TIMESTAMP"
print_step "Building Docker image: $NEW_IMAGE"

docker build --no-cache --platform linux/amd64 -f Dockerfile.simple -t $NEW_IMAGE .

print_step "Pushing image to Google Container Registry..."
docker push $NEW_IMAGE

# Also tag as latest
docker tag $NEW_IMAGE $IMAGE_NAME:latest  
docker push $IMAGE_NAME:latest

print_success "Docker image built and pushed"

# Deploy to Cloud Run with direct deployment (no YAML file)
print_step "Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --image=$NEW_IMAGE \
    --region=$REGION \
    --platform=managed \
    --allow-unauthenticated \
    --memory=2Gi \
    --cpu=1 \
    --concurrency=10 \
    --timeout=$TIMEOUT \
    --min-instances=1 \
    --max-instances=10 \
    --port=8080 \
    --set-env-vars="GOOGLE_CLOUD_PROJECT=$PROJECT_ID,ENABLE_STREAMING=true" \
    --service-account="speech-translator@$PROJECT_ID.iam.gserviceaccount.com"

# Get the actual service URL
print_step "Getting service URL..."
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
    --region=$REGION \
    --format="value(status.url)")

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