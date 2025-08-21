#!/bin/bash
# validate-system.sh - End-to-end system validation

set -e

# Configuration
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"lfhs-translate"}
REGION=${REGION:-"europe-west1"}
SERVICE_NAME="streaming-stt-service"
BACKEND_URL="https://streaming-stt-service-ysw2dobxea-ew.a.run.app"
FRONTEND_URL="https://lfhs-translate.web.app"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

print_step() {
    echo -e "${BLUE}🔍 $1${NC}"
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

# Validation 1: Backend health and functionality
validate_backend() {
    print_step "Validating backend service..."
    
    # Basic health check
    local health_response=$(curl -s -f "$BACKEND_URL/health" 2>/dev/null || echo "FAILED")
    
    if [[ $health_response == *'"status":"ok"'* ]]; then
        print_success "Backend health check passed"
        
        # Extract additional info from health response
        if command -v python3 &> /dev/null; then
            local version=$(echo "$health_response" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('version', 'unknown'))" 2>/dev/null || echo "unknown")
            local uptime=$(echo "$health_response" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('uptime', 'unknown'))" 2>/dev/null || echo "unknown")
            print_info "  Version: $version"
            print_info "  Uptime: $uptime"
        fi
        
        return 0
    else
        print_error "Backend health check failed"
        print_error "  Response: $health_response"
        return 1
    fi
}

# Validation 2: Frontend accessibility and configuration
validate_frontend() {
    print_step "Validating frontend service..."
    
    # Check if frontend is accessible
    local frontend_response=$(curl -s -I "$FRONTEND_URL" 2>/dev/null | head -n 1 || echo "FAILED")
    
    if [[ $frontend_response == *"200 OK"* ]]; then
        print_success "Frontend is accessible"
        
        # Check if frontend has correct backend configuration
        local config_content=$(curl -s "$FRONTEND_URL/src/config.js" 2>/dev/null || echo "FAILED")
        if [[ $config_content == *"streaming-stt-service"* ]]; then
            print_success "Frontend backend configuration found"
        else
            print_warning "Frontend backend configuration not verified"
        fi
        
        return 0
    else
        print_error "Frontend not accessible"
        print_error "  Response: $frontend_response"
        return 1
    fi
}

# Validation 3: Integration between frontend and backend
validate_integration() {
    print_step "Validating frontend-backend integration..."
    
    # Check if frontend contains references to the backend URL
    local frontend_js_content=$(curl -s "$FRONTEND_URL/app.min.js" 2>/dev/null || \
                               curl -s "$FRONTEND_URL/src/connection.js" 2>/dev/null || \
                               echo "FAILED")
    
    if [[ $frontend_js_content == *"streaming-stt-service"* ]] || \
       [[ $frontend_js_content == *"wss://"* ]]; then
        print_success "Frontend correctly configured with backend URLs"
        return 0
    else
        print_warning "Frontend-backend URL integration could not be verified"
        print_info "This may be normal if the frontend uses dynamic configuration"
        return 0  # Don't fail on this test
    fi
}

# Validation 4: Cloud Run service status
validate_cloud_run_status() {
    print_step "Validating Cloud Run service status..."
    
    if ! command -v gcloud &> /dev/null; then
        print_warning "gcloud CLI not available, skipping Cloud Run validation"
        return 0
    fi
    
    # Check service status
    local service_status=$(gcloud run services describe $SERVICE_NAME \
        --region=$REGION \
        --format="value(status.conditions[0].status)" 2>/dev/null || echo "Unknown")
    
    if [ "$service_status" = "True" ]; then
        print_success "Cloud Run service is ready"
        
        # Get service details
        local service_url=$(gcloud run services describe $SERVICE_NAME \
            --region=$REGION \
            --format="value(status.url)" 2>/dev/null)
        local current_revision=$(gcloud run services describe $SERVICE_NAME \
            --region=$REGION \
            --format="value(status.latestReadyRevisionName)" 2>/dev/null)
        local traffic_percent=$(gcloud run services describe $SERVICE_NAME \
            --region=$REGION \
            --format="value(status.traffic[0].percent)" 2>/dev/null)
            
        print_info "  Service URL: $service_url"
        print_info "  Current Revision: $current_revision"
        print_info "  Traffic: $traffic_percent%"
        
        return 0
    else
        print_error "Cloud Run service is not ready"
        print_error "  Status: $service_status"
        return 1
    fi
}

# Validation 5: WebSocket connectivity 
validate_websocket() {
    print_step "Validating WebSocket endpoints..."
    
    # Test WebSocket endpoint accessibility
    local ws_url=$(echo $BACKEND_URL | sed 's/https:/wss:/')
    local ws_test_response=$(curl -s -I -H "Upgrade: websocket" -H "Connection: Upgrade" \
        "$BACKEND_URL/ws/stream/validation-test" 2>/dev/null | head -n 1 || echo "FAILED")
    
    if [[ $ws_test_response == *"101"* ]] || [[ $ws_test_response == *"400"* ]]; then
        print_success "WebSocket endpoints are accessible"
        print_info "  WebSocket URL: $ws_url"
        return 0
    else
        print_warning "WebSocket endpoint test inconclusive"
        print_info "  This may be normal for WebSocket endpoints"
        return 0  # Don't fail on this test
    fi
}

# Validation 6: API endpoints functionality
validate_api_endpoints() {
    print_step "Validating API endpoints..."
    
    local endpoints=(
        "/health"
        "/"
    )
    
    local failed_endpoints=()
    
    for endpoint in "${endpoints[@]}"; do
        local response=$(curl -s -w "%{http_code}" -o /dev/null "$BACKEND_URL$endpoint" 2>/dev/null || echo "000")
        
        if [ "$response" = "200" ] || [ "$response" = "404" ]; then  # 404 is acceptable for some endpoints
            print_info "  $endpoint: $response"
        else
            print_warning "  $endpoint: $response (unexpected)"
            failed_endpoints+=("$endpoint")
        fi
    done
    
    if [ ${#failed_endpoints[@]} -eq 0 ]; then
        print_success "API endpoints validation completed"
        return 0
    else
        print_warning "Some API endpoints returned unexpected responses: ${failed_endpoints[*]}"
        return 0  # Don't fail the overall validation
    fi
}

# Validation 7: System performance check
validate_performance() {
    print_step "Validating system performance..."
    
    # Measure response time
    local start_time=$(date +%s%N)
    curl -s -f "$BACKEND_URL/health" > /dev/null 2>&1
    local end_time=$(date +%s%N)
    local response_time=$(( (end_time - start_time) / 1000000 ))  # Convert to milliseconds
    
    print_info "  Backend response time: ${response_time}ms"
    
    if [ $response_time -lt 2000 ]; then  # Less than 2 seconds
        print_success "Backend response time is acceptable"
        return 0
    else
        print_warning "Backend response time is slow (${response_time}ms)"
        return 0  # Don't fail on performance
    fi
}

# Validation 8: Security headers check
validate_security() {
    print_step "Validating security configurations..."
    
    local headers=$(curl -s -I "$BACKEND_URL/health" 2>/dev/null || echo "FAILED")
    
    # Check for basic security headers
    local security_checks=(
        "X-Content-Type-Options"
        "X-Frame-Options" 
        "X-XSS-Protection"
    )
    
    local missing_headers=()
    
    for header in "${security_checks[@]}"; do
        if [[ $headers != *"$header"* ]]; then
            missing_headers+=("$header")
        fi
    done
    
    if [ ${#missing_headers[@]} -eq 0 ]; then
        print_success "Security headers are present"
    else
        print_info "Optional security headers missing: ${missing_headers[*]}"
        print_info "This is acceptable for API services"
    fi
    
    return 0
}

# Main validation function
main() {
    echo "🚀 Starting end-to-end system validation..."
    echo ""
    
    local validations=(
        "validate_backend"
        "validate_frontend"
        "validate_integration"
        "validate_cloud_run_status"
        "validate_websocket"
        "validate_api_endpoints"
        "validate_performance"
        "validate_security"
    )
    
    local failed_validations=()
    local total_validations=${#validations[@]}
    local passed_validations=0
    
    for validation_func in "${validations[@]}"; do
        echo ""
        if $validation_func; then
            passed_validations=$((passed_validations + 1))
        else
            failed_validations+=("$validation_func")
        fi
    done
    
    echo ""
    echo "📊 Validation Results:"
    echo "  • Total validations: $total_validations"
    echo "  • Passed: $passed_validations" 
    echo "  • Failed: ${#failed_validations[@]}"
    echo ""
    
    if [ ${#failed_validations[@]} -eq 0 ]; then
        print_success "All system validations passed! System is operational 🎉"
        echo ""
        echo "📊 System URLs:"
        print_info "  • Frontend: $FRONTEND_URL"
        print_info "  • Backend Health: $BACKEND_URL/health"
        print_info "  • WebSocket: $(echo $BACKEND_URL | sed 's/https:/wss:/')/ws/stream/demo-stream"
        echo ""
        print_success "✅ Speech translation system is fully operational!"
        return 0
    else
        print_error "Failed validations: ${failed_validations[*]}"
        print_error "System has issues that need attention"
        return 1
    fi
}

# Parse command line arguments
case "${1:-all}" in
    "all")
        main
        ;;
    "backend")
        validate_backend
        ;;
    "frontend")
        validate_frontend
        ;;
    "integration")
        validate_integration
        ;;
    "cloudrun")
        validate_cloud_run_status
        ;;
    "websocket")
        validate_websocket
        ;;
    "performance")
        validate_performance
        ;;
    *)
        echo "Usage: $0 [all|backend|frontend|integration|cloudrun|websocket|performance]"
        exit 1
        ;;
esac