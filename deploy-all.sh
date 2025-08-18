#!/bin/bash
set -e

# Master Deployment Script for Streaming STT Application
echo "🚀 Starting Complete Deployment of Streaming STT Application..."

# Configuration
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"lfhs-translate"}

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

print_header() {
    echo ""
    echo "=================================="
    echo -e "${BLUE}$1${NC}"
    echo "=================================="
    echo ""
}

# Validate prerequisites
print_step "Validating prerequisites..."

MISSING_TOOLS=()

if ! command -v gcloud &> /dev/null; then
    MISSING_TOOLS+=("gcloud CLI")
fi

if ! command -v docker &> /dev/null; then
    MISSING_TOOLS+=("Docker")
fi

if ! command -v firebase &> /dev/null; then
    MISSING_TOOLS+=("Firebase CLI")
fi

if ! command -v node &> /dev/null; then
    MISSING_TOOLS+=("Node.js")
fi

if [ ${#MISSING_TOOLS[@]} -gt 0 ]; then
    print_error "Missing required tools:"
    printf ' • %s\n' "${MISSING_TOOLS[@]}"
    exit 1
fi

# Check authentication
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    print_error "Not authenticated with gcloud. Please run: gcloud auth login"
    exit 1
fi

if ! firebase projects:list &> /dev/null; then
    print_error "Not authenticated with Firebase. Please run: firebase login"
    exit 1
fi

print_success "All prerequisites satisfied"

# Set project
gcloud config set project $PROJECT_ID

print_header "PHASE 1: BACKEND DEPLOYMENT"

# Deploy backend
print_step "Deploying backend to Cloud Run..."
if [ ! -f "./deploy-backend.sh" ]; then
    print_error "Backend deployment script not found: ./deploy-backend.sh"
    exit 1
fi

./deploy-backend.sh

if [ $? -ne 0 ]; then
    print_error "Backend deployment failed!"
    exit 1
fi

print_success "Backend deployment completed"

print_header "PHASE 2: FRONTEND DEPLOYMENT"

# Deploy frontend
print_step "Deploying frontend to Firebase..."
if [ ! -f "./frontend/deploy-frontend.sh" ]; then
    print_error "Frontend deployment script not found: ./frontend/deploy-frontend.sh"
    exit 1
fi

cd frontend
./deploy-frontend.sh

if [ $? -ne 0 ]; then
    print_error "Frontend deployment failed!"
    exit 1
fi

cd ..
print_success "Frontend deployment completed"

print_header "PHASE 3: END-TO-END VERIFICATION"

# Get URLs for verification
SERVICE_NAME="streaming-stt-service"
REGION="europe-west1"

BACKEND_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)" 2>/dev/null || \
              gcloud run services describe "hybrid-stt-service" --region=$REGION --format="value(status.url)" 2>/dev/null)
FRONTEND_URL="https://$PROJECT_ID.web.app"

print_step "Running end-to-end verification..."

# Test backend
print_step "Testing backend health..."
BACKEND_HEALTH=$(curl -s -f "$BACKEND_URL/health" || echo "FAILED")
if [[ $BACKEND_HEALTH == *"\"status\":\"ok\""* ]]; then
    print_success "Backend health check passed"
else
    print_error "Backend health check failed"
    echo "Response: $BACKEND_HEALTH"
    exit 1
fi

# Test frontend
print_step "Testing frontend accessibility..."
sleep 5  # Allow time for Firebase deployment to propagate
FRONTEND_RESPONSE=$(curl -s -f "$FRONTEND_URL" | head -1 || echo "FAILED")
if [[ $FRONTEND_RESPONSE == *"<!DOCTYPE html>"* ]]; then
    print_success "Frontend accessibility test passed"
else
    print_error "Frontend accessibility test failed"
    echo "Response: $FRONTEND_RESPONSE"
    exit 1
fi

# Test frontend-backend configuration alignment
print_step "Testing frontend-backend configuration..."
BACKEND_WS_URL=$(echo $BACKEND_URL | sed 's/https:/wss:/')
FRONTEND_CONFIG=$(curl -s "$FRONTEND_URL/app.min.js" | grep -o "$(echo $BACKEND_WS_URL | sed 's|wss://||')" || echo "NOT_FOUND")

if [[ $FRONTEND_CONFIG != "NOT_FOUND" ]]; then
    print_success "Frontend-backend configuration verified"
else
    print_error "Frontend-backend configuration mismatch!"
    exit 1
fi

# Show final deployment summary
print_header "DEPLOYMENT SUMMARY"

# Get additional details
CURRENT_REVISION=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.latestReadyRevisionName)" 2>/dev/null || \
                   gcloud run services describe "hybrid-stt-service" --region=$REGION --format="value(status.latestReadyRevisionName)")

echo -e "${GREEN}🎉 Complete Streaming STT Application Deployed Successfully!${NC}"
echo ""
echo -e "${BLUE}📊 Deployment Details:${NC}"
echo "  • Project: $PROJECT_ID"
echo "  • Backend Service: $(basename $BACKEND_URL)"
echo "  • Backend Revision: $CURRENT_REVISION"
echo "  • Frontend URL: $FRONTEND_URL"
echo "  • Backend URL: $BACKEND_URL"
echo "  • WebSocket URL: $BACKEND_WS_URL"
echo ""
echo -e "${YELLOW}🧪 Test Your Deployment:${NC}"
echo "  1. Open: $FRONTEND_URL"
echo "  2. Click 'Start Uitzending' to test streaming"
echo "  3. Speak Dutch to test translation"
echo ""
echo -e "${YELLOW}🔧 Monitoring:${NC}"
echo "  • Backend Logs: gcloud run services logs tail $SERVICE_NAME --region=$REGION"
echo "  • Backend Health: curl $BACKEND_URL/health"
echo "  • Firebase Console: https://console.firebase.google.com/project/$PROJECT_ID"
echo ""
echo -e "${YELLOW}🎯 Expected Behavior:${NC}"
echo "  • WebSocket connects to: $BACKEND_WS_URL/ws/stream/demo-stream"
echo "  • Audio chunks: 250ms (8236 bytes)"
echo "  • STT Results: Interim + Final transcripts"
echo "  • Translation: Dutch → English"
echo "  • Output: Translated English audio"
echo ""
echo -e "${GREEN}✅ Ready for streaming speech translation! 🚀${NC}"