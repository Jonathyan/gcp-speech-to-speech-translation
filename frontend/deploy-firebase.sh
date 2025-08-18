#!/bin/bash
set -e

# Firebase Deployment Script for Live Speech Translation Frontend
echo "🚀 Deploying Frontend to Firebase Hosting..."

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

# Check if Firebase CLI is installed
if ! command -v firebase &> /dev/null; then
    print_error "Firebase CLI is not installed. Please install it first:"
    echo "npm install -g firebase-tools"
    exit 1
fi

# Check if user is logged in to Firebase
if ! firebase projects:list &> /dev/null; then
    print_error "Not authenticated with Firebase. Please run:"
    echo "firebase login"
    exit 1
fi

# Build production assets
print_step "Building production assets..."
npm run build

if [ $? -ne 0 ]; then
    print_error "Build failed"
    exit 1
fi

print_success "Build completed"

# Verify build output
print_step "Verifying build output..."
if [ ! -f "dist/index.html" ]; then
    print_error "Build output missing - dist/index.html not found"
    exit 1
fi

if [ ! -f "dist/app.min.js" ]; then
    print_error "Build output missing - dist/app.min.js not found"
    exit 1
fi

print_success "Build output verified"

# Check Firebase project configuration
print_step "Checking Firebase project configuration..."
PROJECT_ID=$(firebase use | grep -o "lfhs-translate" || echo "")

if [ -z "$PROJECT_ID" ]; then
    print_warning "Firebase project not set. Setting to lfhs-translate..."
    firebase use lfhs-translate
    
    if [ $? -ne 0 ]; then
        print_error "Failed to set Firebase project"
        exit 1
    fi
fi

print_success "Firebase project configured: lfhs-translate"

# Deploy to Firebase Hosting
print_step "Deploying to Firebase Hosting..."
firebase deploy --only hosting

if [ $? -eq 0 ]; then
    print_success "Deployment completed!"
    
    # Get the deployed URL
    HOSTING_URL=$(firebase hosting:sites:get lfhs-translate 2>/dev/null | grep -o "https://[^[:space:]]*" || echo "https://lfhs-translate.firebaseapp.com")
    
    echo ""
    echo -e "${GREEN}🎉 Frontend successfully deployed!${NC}"
    echo -e "${BLUE}Live URL: $HOSTING_URL${NC}"
    echo ""
    echo -e "${YELLOW}📊 Next Steps:${NC}"
    echo "1. Test the live application at the URL above"
    echo "2. Test speaker/listener functionality"
    echo "3. Verify WebSocket connections to Cloud Run backend"
    echo "4. Monitor performance and error rates"
    echo ""
    echo -e "${YELLOW}🔧 Testing Commands:${NC}"
    echo "curl $HOSTING_URL/health"
    echo ""
    echo -e "${YELLOW}🎯 WebSocket Endpoints:${NC}"
    echo "Speaker:  wss://hybrid-stt-service-ysw2dobxea-ew.a.run.app/ws/speak/{stream_id}"
    echo "Listener: wss://hybrid-stt-service-ysw2dobxea-ew.a.run.app/ws/listen/{stream_id}"
    echo ""
    echo -e "${GREEN}Ready for production use! 🚀${NC}"
    
else
    print_error "Deployment failed"
    exit 1
fi