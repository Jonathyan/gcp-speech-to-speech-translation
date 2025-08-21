#!/bin/bash
set -e

# Robust Frontend Deployment Script for Firebase
echo "🚀 Deploying Streaming STT Frontend to Firebase..."

# Configuration
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"lfhs-translate"}
BACKEND_SERVICE_NAME="streaming-stt-service"
BACKEND_REGION="europe-west1"

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

if ! command -v firebase &> /dev/null; then
    print_error "Firebase CLI is not installed. Please install it first:"
    echo "npm install -g firebase-tools"
    exit 1
fi

if ! command -v gcloud &> /dev/null; then
    print_error "gcloud CLI is not installed. Please install it first."
    exit 1
fi

if ! command -v node &> /dev/null; then
    print_error "Node.js is not installed. Please install it first."
    exit 1
fi

# Check authentication
if ! firebase projects:list &> /dev/null; then
    print_error "Not authenticated with Firebase. Please run: firebase login"
    exit 1
fi

if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    print_error "Not authenticated with gcloud. Please run: gcloud auth login"
    exit 1
fi

# Set gcloud project
gcloud config set project $PROJECT_ID

# Auto-detect backend URL
print_step "Auto-detecting backend URL..."
BACKEND_URL=""

# Function to get backend URL with fallback
get_backend_url() {
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

# Try the new service name first
if gcloud run services describe $BACKEND_SERVICE_NAME --region=$BACKEND_REGION &> /dev/null; then
    BACKEND_URL=$(get_backend_url "$BACKEND_SERVICE_NAME" "$BACKEND_REGION")
    if [ ! -z "$BACKEND_URL" ]; then
        print_success "Found backend service: $BACKEND_SERVICE_NAME"
    else
        print_error "Could not get URL for service: $BACKEND_SERVICE_NAME"
        exit 1
    fi
# Fallback to old service name
elif gcloud run services describe "streaming-stt-service" --region=$BACKEND_REGION &> /dev/null; then
    BACKEND_URL=$(get_backend_url "streaming-stt-service" "$BACKEND_REGION")
    if [ ! -z "$BACKEND_URL" ]; then
        print_warning "Using fallback service: streaming-stt-service"
    else
        print_error "Could not get URL for service: streaming-stt-service"
        exit 1
    fi
else
    print_error "No backend service found! Please deploy the backend first."
    exit 1
fi

# Convert HTTP to WebSocket URL
BACKEND_WS_URL=$(echo $BACKEND_URL | sed 's/https:/wss:/')
print_success "Backend WebSocket URL: $BACKEND_WS_URL"

# Test backend health before proceeding
print_step "Testing backend health..."
HEALTH_RESPONSE=$(curl -s -f "$BACKEND_URL/health" || echo "FAILED")

if [[ $HEALTH_RESPONSE == *"\"status\":\"ok\""* ]]; then
    print_success "Backend is healthy!"
else
    print_error "Backend health check failed! Response: $HEALTH_RESPONSE"
    exit 1
fi

# Update frontend configuration
print_step "Updating frontend configuration..."
CONFIG_FILE="src/config.js"

if [ ! -f "$CONFIG_FILE" ]; then
    print_error "Configuration file not found: $CONFIG_FILE"
    exit 1
fi

# Create backup
cp "$CONFIG_FILE" "$CONFIG_FILE.backup"

# Update the production WebSocket URL
sed -i.tmp "s|production: 'wss://[^']*'|production: '$BACKEND_WS_URL'|g" "$CONFIG_FILE"

# Verify the change was made
if grep -q "$BACKEND_WS_URL" "$CONFIG_FILE"; then
    print_success "Configuration updated with backend URL"
else
    print_error "Failed to update configuration"
    mv "$CONFIG_FILE.backup" "$CONFIG_FILE"
    exit 1
fi

# Clean up temp file
rm -f "$CONFIG_FILE.tmp"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    print_step "Installing dependencies..."
    npm install
fi

# Build production assets
print_step "Building production assets..."
npm run build

if [ $? -ne 0 ]; then
    print_error "Build failed"
    mv "$CONFIG_FILE.backup" "$CONFIG_FILE"
    exit 1
fi

print_success "Build completed"

# Verify build output
print_step "Verifying build output..."
REQUIRED_FILES=("dist/index.html" "dist/app.min.js" "dist/styles.css")

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        print_error "Build output missing: $file"
        mv "$CONFIG_FILE.backup" "$CONFIG_FILE"
        exit 1
    fi
done

# Verify the backend URL is in the built assets
if ! grep -q "$(echo $BACKEND_WS_URL | sed 's|wss://||')" "dist/app.min.js"; then
    print_error "Backend URL not found in built assets!"
    mv "$CONFIG_FILE.backup" "$CONFIG_FILE"
    exit 1
fi

print_success "Build output verified with correct backend URL"

# Check Firebase project configuration
print_step "Checking Firebase project configuration..."
CURRENT_PROJECT=$(firebase use | grep -o "$PROJECT_ID" || echo "")

if [ -z "$CURRENT_PROJECT" ]; then
    print_warning "Firebase project not set. Setting to $PROJECT_ID..."
    firebase use $PROJECT_ID
    
    if [ $? -ne 0 ]; then
        print_error "Failed to set Firebase project to $PROJECT_ID"
        mv "$CONFIG_FILE.backup" "$CONFIG_FILE"
        exit 1
    fi
fi

print_success "Firebase project configured: $PROJECT_ID"

# Deploy to Firebase Hosting
print_step "Deploying to Firebase Hosting..."
firebase deploy --only hosting

if [ $? -eq 0 ]; then
    print_success "Deployment completed!"
    
    # Get the deployed URL
    HOSTING_URL="https://$PROJECT_ID.web.app"
    
    # Test the deployed frontend
    print_step "Testing deployed frontend..."
    sleep 5  # Wait for deployment to propagate
    
    FRONTEND_RESPONSE=$(curl -s -f "$HOSTING_URL" | head -1 || echo "FAILED")
    if [[ $FRONTEND_RESPONSE == *"<!DOCTYPE html>"* ]]; then
        print_success "Frontend is accessible!"
    else
        print_warning "Frontend accessibility test inconclusive"
    fi
    
    # Test if the correct backend URL is deployed
    DEPLOYED_CONFIG=$(curl -s "$HOSTING_URL/app.min.js" | grep -o "$(echo $BACKEND_WS_URL | sed 's|wss://||')" || echo "NOT_FOUND")
    if [[ $DEPLOYED_CONFIG != "NOT_FOUND" ]]; then
        print_success "Correct backend URL found in deployed assets!"
    else
        print_warning "Could not verify backend URL in deployed assets"
    fi
    
    # Clean up backup
    rm -f "$CONFIG_FILE.backup"
    
    echo ""
    echo -e "${GREEN}🎉 Frontend deployment verified and ready!${NC}"
    echo -e "${BLUE}Live URL: $HOSTING_URL${NC}"
    echo -e "${BLUE}Backend URL: $BACKEND_WS_URL${NC}"
    echo ""
    echo -e "${YELLOW}📊 Connection Test:${NC}"
    echo "  • Frontend: $HOSTING_URL"
    echo "  • Backend Health: $BACKEND_URL/health"
    echo "  • WebSocket: $BACKEND_WS_URL/ws/stream/demo-stream"
    echo ""
    echo -e "${YELLOW}🧪 Test Commands:${NC}"
    echo "  curl $HOSTING_URL"
    echo "  curl $BACKEND_URL/health"
    echo ""
    echo -e "${GREEN}✅ End-to-end deployment completed! 🚀${NC}"
    
else
    print_error "Deployment failed"
    mv "$CONFIG_FILE.backup" "$CONFIG_FILE"
    exit 1
fi