#!/bin/bash
set -e

# Phase 2 Hybrid STT Service Deployment Script for Cloud Run
echo "🚀 Deploying Phase 2 Hybrid STT Service to Cloud Run..."

# Configuration
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"lfhs-translate"}
REGION=${REGION:-"europe-west1"}
SERVICE_NAME="hybrid-stt-service"
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"

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

# Create service account if it doesn't exist
print_step "Setting up service account..."
SERVICE_ACCOUNT="speech-translator@$PROJECT_ID.iam.gserviceaccount.com"

# if ! gcloud iam service-accounts describe $SERVICE_ACCOUNT &> /dev/null; then
#     gcloud iam service-accounts create speech-translator \
#         --display-name="speech-translator Service Account" \
#         --description="Service account for Phase 2 Hybrid STT Service"
    
#     # Grant necessary permissions
#     gcloud projects add-iam-policy-binding $PROJECT_ID \
#         --member="serviceAccount:$SERVICE_ACCOUNT" \
#         --role="roles/speech.editor"
    
#     gcloud projects add-iam-policy-binding $PROJECT_ID \
#         --member="serviceAccount:$SERVICE_ACCOUNT" \
#         --role="roles/translate.editor" 
    
#     gcloud projects add-iam-policy-binding $PROJECT_ID \
#         --member="serviceAccount:$SERVICE_ACCOUNT" \
#         --role="roles/texttospeech.editor"
    
#     gcloud projects add-iam-policy-binding $PROJECT_ID \
#         --member="serviceAccount:$SERVICE_ACCOUNT" \
#         --role="roles/logging.logWriter"
    
#     gcloud projects add-iam-policy-binding $PROJECT_ID \
#         --member="serviceAccount:$SERVICE_ACCOUNT" \
#         --role="roles/monitoring.metricWriter"
    
#     print_success "Service account created and configured"
# else
#     print_success "Service account already exists"
# fi

# Build and push Docker image
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
print_step "Building Docker image for linux/amd64 platform..."
docker build --platform linux/amd64 -f Dockerfile.simple -t $IMAGE_NAME:$TIMESTAMP .

print_step "Pushing image to Google Container Registry..."
docker push $IMAGE_NAME:$TIMESTAMP

# Also tag as latest
docker tag $IMAGE_NAME:$TIMESTAMP $IMAGE_NAME:latest
docker push $IMAGE_NAME:latest

print_success "Docker image built and pushed"

# Update service configuration with actual project ID and timestamp
print_step "Updating service configuration..."
sed -i.bak "s/PROJECT_ID/$PROJECT_ID/g" cloud-run-service.yaml
sed -i.bak2 "s/:latest/:$TIMESTAMP/g" cloud-run-service.yaml

# Deploy to Cloud Run
print_step "Deploying to Cloud Run..."
gcloud run services replace cloud-run-service.yaml \
    --region=$REGION

# Set IAM policy to allow public access (modify as needed)
print_step "Setting IAM policy..."
gcloud run services add-iam-policy-binding $SERVICE_NAME \
    --region=$REGION \
    --member="allUsers" \
    --role="roles/run.invoker"

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
    --region=$REGION \
    --format="value(status.url)")

# Clean up temporary files
rm -f cloud-run-service.yaml.bak cloud-run-service.yaml.bak2

print_success "Deployment completed!"
echo ""
echo -e "${GREEN}🎉 Phase 2 Hybrid STT Service is now live!${NC}"
echo -e "${BLUE}Service URL: $SERVICE_URL${NC}"
echo ""
echo -e "${YELLOW}📊 Monitoring and Logs:${NC}"
echo "  • Logs: https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME/logs"
echo "  • Metrics: https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME/metrics"
echo "  • Service: https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME"
echo ""
echo -e "${YELLOW}🔧 Configuration:${NC}"
echo "  • Streaming enabled: true"
echo "  • Quality threshold: 0.7"  
echo "  • Max concurrent sessions: 20"
echo "  • Auto-scaling: 1-10 instances"
echo ""
echo -e "${YELLOW}🧪 Test the deployment:${NC}"
echo "  curl $SERVICE_URL/health"
echo ""
echo -e "${GREEN}Ready for Phase 2 hybrid streaming! 🚀${NC}"