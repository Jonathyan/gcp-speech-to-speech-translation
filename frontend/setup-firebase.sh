#!/bin/bash
set -e

# Firebase Setup Script for Live Speech Translation Frontend
echo "🔥 Setting up Firebase hosting for Live Speech Translation..."

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
print_step "Checking Firebase CLI installation..."
if ! command -v firebase &> /dev/null; then
    print_error "Firebase CLI is not installed. Installing now..."
    npm install -g firebase-tools
    print_success "Firebase CLI installed"
else
    print_success "Firebase CLI is already installed"
fi

# Check if user is logged in
print_step "Checking Firebase authentication..."
if ! firebase projects:list &> /dev/null; then
    print_warning "Not authenticated with Firebase"
    echo ""
    echo "Please run the following commands to set up Firebase:"
    echo ""
    echo -e "${YELLOW}1. Login to Firebase:${NC}"
    echo "   firebase login"
    echo ""
    echo -e "${YELLOW}2. List your projects:${NC}"
    echo "   firebase projects:list"
    echo ""
    echo -e "${YELLOW}3. If 'lfhs-translate' doesn't exist, create it:${NC}"
    echo "   - Go to https://console.firebase.google.com"
    echo "   - Click 'Create a project'"
    echo "   - Use project ID: lfhs-translate"
    echo "   - Enable Firebase Hosting in the console"
    echo ""
    echo -e "${YELLOW}4. Then initialize hosting:${NC}"
    echo "   firebase use lfhs-translate"
    echo "   firebase init hosting"
    echo ""
    echo -e "${YELLOW}5. Finally deploy:${NC}"
    echo "   ./deploy-firebase.sh"
    echo ""
    exit 1
fi

print_success "Firebase authentication verified"

# List available projects
print_step "Available Firebase projects:"
firebase projects:list

# Check if lfhs-translate project exists
print_step "Checking for lfhs-translate project..."
if firebase projects:list | grep -q "lfhs-translate"; then
    print_success "Found lfhs-translate project"
    
    # Set the project
    firebase use lfhs-translate
    print_success "Set project to lfhs-translate"
    
    # Check if hosting is initialized
    if [ ! -f "firebase.json" ]; then
        print_warning "Firebase hosting not initialized"
        print_step "Initializing Firebase hosting..."
        
        # Use non-interactive initialization
        firebase init hosting --project lfhs-translate
        print_success "Firebase hosting initialized"
    else
        print_success "Firebase hosting already configured"
    fi
    
    print_success "Setup complete! Ready to deploy."
    echo ""
    echo -e "${GREEN}🚀 Next step: Run deployment script${NC}"
    echo "   ./deploy-firebase.sh"
    
else
    print_error "Project 'lfhs-translate' not found"
    echo ""
    echo "Please create the Firebase project first:"
    echo ""
    echo -e "${YELLOW}Option 1 - Create via Firebase Console:${NC}"
    echo "1. Go to https://console.firebase.google.com"
    echo "2. Click 'Create a project'"
    echo "3. Use project ID: lfhs-translate"
    echo "4. Enable Firebase Hosting"
    echo ""
    echo -e "${YELLOW}Option 2 - Use existing GCP project:${NC}"
    echo "1. Go to https://console.firebase.google.com"
    echo "2. Click 'Add project'"
    echo "3. Select existing GCP project 'lfhs-translate'"
    echo "4. Add Firebase to the project"
    echo "5. Enable Firebase Hosting"
    echo ""
    echo -e "${YELLOW}Then run this script again:${NC}"
    echo "   ./setup-firebase.sh"
    echo ""
fi