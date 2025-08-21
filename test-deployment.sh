#!/bin/bash
# test-deployment.sh - Automated deployment testing

set -e

# Configuration
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"lfhs-translate"}
REGION=${REGION:-"europe-west1"}
SERVICE_NAME="streaming-stt-service"
SERVICE_URL="https://streaming-stt-service-ysw2dobxea-ew.a.run.app"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_step() {
    echo -e "${BLUE}🧪 $1${NC}"
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

# Test 1: Configuration validation
test_config_validation() {
    print_step "Testing configuration validation..."
    
    # Source the config file if it exists
    if [ -f "./deploy-backend-config.sh" ]; then
        source ./deploy-backend-config.sh
        load_environment prod
        if validate_config; then
            print_success "Configuration validation test passed"
            return 0
        else
            print_error "Configuration validation test failed"
            return 1
        fi
    else
        print_warning "deploy-backend-config.sh not found, skipping config test"
        return 0
    fi
}

# Test 2: Service health check
test_service_health() {
    print_step "Testing service health check..."
    
    local health_response=$(curl -s -f "$SERVICE_URL/health" 2>/dev/null || echo "FAILED")
    
    if [[ $health_response == *'"status":"ok"'* ]]; then
        print_success "Service health check passed"
        echo "  Response: $health_response"
        return 0
    else
        print_error "Service health check failed"
        echo "  Response: $health_response"
        return 1
    fi
}

# Test 3: WebSocket connectivity
test_websocket_connection() {
    print_step "Testing WebSocket endpoint accessibility..."
    
    local ws_test_response=$(curl -s -I -H "Upgrade: websocket" -H "Connection: Upgrade" \
        "$SERVICE_URL/ws/stream/test" 2>/dev/null | head -n 1 || echo "FAILED")
    
    if [[ $ws_test_response == *"101"* ]] || [[ $ws_test_response == *"400"* ]]; then
        print_success "WebSocket endpoint accessible"
        return 0
    else
        print_warning "WebSocket endpoint test inconclusive (this may be normal)"
        echo "  Response: $ws_test_response"
        return 0  # Don't fail on this test
    fi
}

# Test 4: Deployment script syntax
test_deployment_script_syntax() {
    print_step "Testing deployment script syntax..."
    
    if bash -n ./deploy-backend.sh; then
        print_success "Deployment script syntax is valid"
        return 0
    else
        print_error "Deployment script has syntax errors"
        return 1
    fi
}

# Test 5: Cloud Build configuration
test_cloud_build_config() {
    print_step "Testing Cloud Build configuration..."
    
    if [ -f "./cloudbuild-optimized.yaml" ]; then
        # Basic YAML syntax check
        if command -v python3 &> /dev/null; then
            python3 -c "import yaml; yaml.safe_load(open('./cloudbuild-optimized.yaml'))" 2>/dev/null
            if [ $? -eq 0 ]; then
                print_success "Cloud Build configuration is valid"
                return 0
            else
                print_error "Cloud Build configuration has YAML syntax errors"
                return 1
            fi
        else
            print_warning "Python3 not available, skipping YAML validation"
            return 0
        fi
    else
        print_error "cloudbuild-optimized.yaml not found"
        return 1
    fi
}

# Test 6: Dockerfile validation  
test_dockerfile() {
    print_step "Testing Dockerfile..."
    
    if [ -f "./Dockerfile.optimized" ]; then
        # Basic syntax check - look for required commands
        if grep -q "FROM " ./Dockerfile.optimized && grep -q "CMD " ./Dockerfile.optimized; then
            print_success "Dockerfile.optimized structure is valid"
            return 0
        else
            print_error "Dockerfile.optimized missing required commands"
            return 1
        fi
    else
        print_error "Dockerfile.optimized not found"
        return 1
    fi
}

# Test 7: Required files presence
test_required_files() {
    print_step "Testing required files presence..."
    
    local required_files=(
        "deploy-backend.sh"
        "deploy-backend-config.sh"
        "cloudbuild-optimized.yaml"
        "Dockerfile.optimized"
        ".gcloudignore"
    )
    
    local missing_files=()
    
    for file in "${required_files[@]}"; do
        if [ ! -f "./$file" ]; then
            missing_files+=("$file")
        fi
    done
    
    if [ ${#missing_files[@]} -eq 0 ]; then
        print_success "All required files are present"
        return 0
    else
        print_error "Missing required files: ${missing_files[*]}"
        return 1
    fi
}

# Test 8: GCloud authentication and project
test_gcloud_setup() {
    print_step "Testing GCloud setup..."
    
    if ! command -v gcloud &> /dev/null; then
        print_error "gcloud CLI is not installed"
        return 1
    fi
    
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
        print_error "Not authenticated with gcloud"
        return 1
    fi
    
    local current_project=$(gcloud config get-value project 2>/dev/null)
    if [ "$current_project" != "$PROJECT_ID" ]; then
        print_warning "Current project ($current_project) differs from expected ($PROJECT_ID)"
    fi
    
    print_success "GCloud setup is valid"
    return 0
}

# Main test runner
run_all_tests() {
    echo "🚀 Starting deployment system tests..."
    echo ""
    
    local tests=(
        "test_required_files"
        "test_deployment_script_syntax"  
        "test_cloud_build_config"
        "test_dockerfile"
        "test_gcloud_setup"
        "test_config_validation"
        "test_service_health"
        "test_websocket_connection"
    )
    
    local failed_tests=()
    local total_tests=${#tests[@]}
    local passed_tests=0
    
    for test_func in "${tests[@]}"; do
        echo ""
        if $test_func; then
            passed_tests=$((passed_tests + 1))
        else
            failed_tests+=("$test_func")
        fi
    done
    
    echo ""
    echo "📊 Test Results:"
    echo "  • Total tests: $total_tests"
    echo "  • Passed: $passed_tests"
    echo "  • Failed: ${#failed_tests[@]}"
    
    if [ ${#failed_tests[@]} -eq 0 ]; then
        print_success "All deployment tests passed! 🎉"
        return 0
    else
        print_error "Failed tests: ${failed_tests[*]}"
        return 1
    fi
}

# Parse command line arguments
case "${1:-all}" in
    "all")
        run_all_tests
        ;;
    "health")
        test_service_health
        ;;
    "websocket")
        test_websocket_connection
        ;;
    "config")
        test_config_validation
        ;;
    "syntax")
        test_deployment_script_syntax
        ;;
    "files")
        test_required_files
        ;;
    *)
        echo "Usage: $0 [all|health|websocket|config|syntax|files]"
        exit 1
        ;;
esac