#!/bin/bash
# deploy-backend-config.sh - Environment configuration

# Production environment
PROD_CONFIG() {
    export PROJECT_ID="lfhs-translate"
    export REGION="europe-west1"  
    export SERVICE_NAME="streaming-stt-service"
    export MIN_INSTANCES=1
    export MAX_INSTANCES=10
    export MEMORY="2Gi"
    export CPU="1"
    export TIMEOUT=600
    export CONCURRENCY=10
}

# Staging environment (for future use)
STAGING_CONFIG() {
    export PROJECT_ID="lfhs-translate"
    export REGION="europe-west1"  
    export SERVICE_NAME="streaming-stt-service-staging"
    export MIN_INSTANCES=0  # Cost optimization
    export MAX_INSTANCES=3
    export MEMORY="1Gi"     # Smaller for staging
    export CPU="0.5"
    export TIMEOUT=600
    export CONCURRENCY=5
}

# Load environment
load_environment() {
    local env=${1:-prod}
    case $env in
        prod)
            PROD_CONFIG
            ;;
        staging)
            STAGING_CONFIG
            ;;
        *)
            echo "Unknown environment: $env"
            echo "Available environments: prod, staging"
            exit 1
            ;;
    esac
    
    echo "🔧 Loaded $env environment configuration"
    echo "  Project: $PROJECT_ID"
    echo "  Service: $SERVICE_NAME"
    echo "  Region: $REGION"
}

# Validation function
validate_config() {
    local required_vars=(
        "PROJECT_ID"
        "REGION"
        "SERVICE_NAME"
        "MIN_INSTANCES"
        "MAX_INSTANCES"
        "MEMORY"
        "CPU"
        "TIMEOUT"
        "CONCURRENCY"
    )
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            echo "❌ Missing required configuration: $var"
            return 1
        fi
    done
    
    echo "✅ Configuration validation passed"
    return 0
}