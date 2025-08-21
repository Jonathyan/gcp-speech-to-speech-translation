# DevOps Iteration 2: Completion Plan

**Date**: August 21, 2025  
**Status**: Iteration 1 ✅ Complete | Iteration 2 🚧 In Progress  
**Goal**: Complete enhanced traffic management with blue-green deployment and zero-downtime releases

---

## 📊 Current State Assessment

### ✅ Completed (Iteration 1)
- **Cloud Build Integration**: Working with optimized caching
  - `cloudbuild-optimized.yaml` - Multi-stage Docker caching
  - `Dockerfile.optimized` - Optimized layers
  - Build time: Reduced from >15min to <5min
  - Machine type: E2_HIGHCPU_32 for faster builds

### 🚧 Partially Completed (Iteration 2)
- **Basic Traffic Management**: Simple `--to-latest` flag
- **Environment Configuration**: `deploy-backend-config.sh` created
- **Multiple Deploy Scripts**: Both standard and optimized versions exist

### ❌ Missing Components (Iteration 2)
- Blue-green deployment functions
- Health check with retries
- Automated rollback mechanisms
- Revision readiness checks
- Comprehensive testing scripts

---

## 🎯 Implementation Tasks

### Task 1: Consolidate Deploy Scripts
**Priority**: CRITICAL  
**Time**: 30 minutes

#### 1.1 Create Unified Deploy Script
Create `deploy-backend-unified.sh` that combines the best of both scripts:
- Optimized build from `deploy-backend-optimized.sh`
- Add blue-green deployment functions
- Include rollback mechanisms
- Integrate health checks with retries

#### 1.2 Script Cleanup Strategy
```bash
# Final structure after consolidation:
deploy-backend.sh          # Main deployment script (unified)
deploy-backend-config.sh   # Environment configuration (keep)

# To be archived/removed:
deploy-backend-optimized.sh  # Archive to scripts/archive/
cloudbuild.yaml              # Remove (replaced by optimized)
Dockerfile.simple            # Remove (replaced by optimized)
```

---

### Task 2: Implement Blue-Green Deployment
**Priority**: HIGH  
**Time**: 1-2 hours

#### 2.1 Add Core Functions to deploy-backend.sh

```bash
# Function: Deploy with Blue-Green Pattern
deploy_with_blue_green() {
    local new_revision=$1
    
    # Get current revision for potential rollback
    local current_revision=$(gcloud run services describe $SERVICE_NAME \
        --region=$REGION \
        --format="value(status.latestReadyRevisionName)")
    
    # Deploy new revision with 0% traffic
    gcloud run services update-traffic $SERVICE_NAME \
        --region=$REGION \
        --to-revisions=$new_revision=0 \
        --quiet
    
    # Health check new revision
    if health_check_revision $new_revision; then
        # Gradually shift traffic (canary approach)
        for percent in 10 30 50 100; do
            print_step "Shifting $percent% traffic to new revision..."
            gcloud run services update-traffic $SERVICE_NAME \
                --region=$REGION \
                --to-revisions=$new_revision=$percent \
                --quiet
            
            sleep 5
            if ! health_check_revision $new_revision; then
                print_error "Health check failed at $percent% traffic"
                rollback_to_revision $current_revision
                return 1
            fi
        done
        print_success "Blue-green deployment completed!"
    else
        rollback_to_revision $current_revision
        return 1
    fi
}
```

#### 2.2 Add Health Check with Retries

```bash
# Function: Enhanced Health Check
health_check_revision() {
    local revision=$1
    local max_attempts=5
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        local response=$(curl -s -w "%{http_code}" -o /tmp/health_response \
            "$SERVICE_URL/health" || echo "000")
        
        if [ "$response" = "200" ]; then
            local body=$(cat /tmp/health_response)
            if [[ $body == *'"status":"ok"'* ]]; then
                return 0
            fi
        fi
        
        attempt=$((attempt + 1))
        [ $attempt -lt $max_attempts ] && sleep 10
    done
    
    return 1
}
```

#### 2.3 Add Rollback Mechanism

```bash
# Function: Automated Rollback
rollback_to_revision() {
    local target_revision=$1
    
    print_warning "Initiating rollback to revision: $target_revision"
    
    gcloud run services update-traffic $SERVICE_NAME \
        --region=$REGION \
        --to-revisions=$target_revision=100 \
        --quiet
    
    if health_check_revision $target_revision; then
        print_success "Rollback successful!"
        return 0
    else
        print_error "Rollback failed - manual intervention required!"
        return 1
    fi
}
```

---

### Task 3: Create Testing & Validation Scripts
**Priority**: MEDIUM  
**Time**: 1 hour

#### 3.1 Create test-deployment.sh
```bash
#!/bin/bash
# test-deployment.sh - Automated deployment testing

set -e
source ./deploy-backend-config.sh

# Test scenarios
run_deployment_test() {
    echo "🧪 Testing deployment process..."
    
    # Test 1: Config validation
    load_environment prod
    validate_config || exit 1
    
    # Test 2: Service health
    curl -f $SERVICE_URL/health || exit 1
    
    # Test 3: WebSocket connectivity
    test_websocket_connection
    
    # Test 4: Rollback simulation
    test_rollback_mechanism
    
    echo "✅ All deployment tests passed!"
}

test_websocket_connection() {
    local ws_url=$(echo $SERVICE_URL | sed 's/https:/wss:/')
    # Add WebSocket test logic
}

test_rollback_mechanism() {
    # Simulate rollback scenario
    echo "Testing rollback mechanism..."
    # Add rollback test logic
}

run_deployment_test
```

#### 3.2 Create validate-system.sh
```bash
#!/bin/bash
# validate-system.sh - End-to-end validation

set -e

validate_backend() {
    echo "🔍 Validating backend..."
    local health_response=$(curl -s https://streaming-stt-service-ysw2dobxea-ew.a.run.app/health)
    
    if [[ $health_response == *'"status":"ok"'* ]]; then
        echo "✅ Backend operational"
        return 0
    else
        echo "❌ Backend health check failed"
        return 1
    fi
}

validate_frontend() {
    echo "🔍 Validating frontend..."
    local frontend_response=$(curl -s -I https://lfhs-translate.web.app | head -n 1)
    
    if [[ $frontend_response == *"200 OK"* ]]; then
        echo "✅ Frontend accessible"
        return 0
    else
        echo "❌ Frontend not accessible"
        return 1
    fi
}

validate_integration() {
    echo "🔍 Validating integration..."
    # Check frontend has correct backend URL
    local config_check=$(curl -s https://lfhs-translate.web.app/src/config.js | grep -o "streaming-stt-service")
    
    if [ ! -z "$config_check" ]; then
        echo "✅ Integration configured correctly"
        return 0
    else
        echo "❌ Integration misconfigured"
        return 1
    fi
}

# Main validation
echo "🚀 Starting system validation..."
validate_backend
validate_frontend
validate_integration
echo "🎉 System validation complete!"
```

---

## 📋 Implementation Checklist

### Phase 1: Script Consolidation (30 min)
- [ ] Backup existing scripts to `scripts/archive/`
- [ ] Create unified `deploy-backend.sh` with all features
- [ ] Test unified script with dry run
- [ ] Remove duplicate/obsolete files

### Phase 2: Blue-Green Implementation (2 hours)
- [ ] Add `deploy_with_blue_green()` function
- [ ] Add `health_check_revision()` with retries
- [ ] Add `rollback_to_revision()` function
- [ ] Add `wait_for_revision_ready()` function
- [ ] Integrate functions into main deployment flow
- [ ] Test blue-green deployment end-to-end

### Phase 3: Testing & Validation (1 hour)
- [ ] Create `test-deployment.sh`
- [ ] Create `validate-system.sh`
- [ ] Run full test suite
- [ ] Document any issues found

### Phase 4: Cleanup & Documentation (30 min)
- [ ] Archive old scripts
- [ ] Update CLAUDE.md with new deployment commands
- [ ] Create deployment runbook
- [ ] Clean up git repository

---

## 🗂️ Final File Structure

```
/
├── deploy-backend.sh              # Main unified deployment script
├── deploy-backend-config.sh       # Environment configuration
├── test-deployment.sh             # Deployment testing
├── validate-system.sh             # System validation
├── cloudbuild-optimized.yaml      # Optimized Cloud Build config
├── Dockerfile.optimized           # Optimized Dockerfile
├── .gcloudignore                  # Build context optimization
└── scripts/
    └── archive/                   # Archived old scripts
        ├── deploy-backend-optimized.sh
        ├── cloudbuild.yaml
        └── Dockerfile.simple
```

---

## 🚀 Execution Steps

### Step 1: Backup Current State
```bash
mkdir -p scripts/archive
cp deploy-backend-optimized.sh scripts/archive/
cp cloudbuild.yaml scripts/archive/ 2>/dev/null || true
cp Dockerfile.simple scripts/archive/ 2>/dev/null || true
```

### Step 2: Update Main Deploy Script
1. Open `deploy-backend.sh`
2. Add blue-green deployment functions
3. Integrate health checks and rollback
4. Test with `--dry-run` flag

### Step 3: Create Test Scripts
```bash
# Create test scripts with proper permissions
touch test-deployment.sh validate-system.sh
chmod +x test-deployment.sh validate-system.sh
```

### Step 4: Run Validation
```bash
./test-deployment.sh
./validate-system.sh
```

### Step 5: Clean Up Repository
```bash
# Remove obsolete files
rm -f deploy-backend-optimized.sh
rm -f cloudbuild.yaml
rm -f Dockerfile.simple

# Stage changes
git add -A
git status
```

---

## ⚠️ Risk Mitigation

### Rollback Plan
If any issues occur during implementation:
1. Keep backup of working `deploy-backend.sh`
2. Test all changes in dry-run mode first
3. Deploy to staging (if available) before production
4. Keep manual rollback commands ready

### Manual Rollback Commands
```bash
# Quick rollback to previous revision
gcloud run services update-traffic streaming-stt-service \
    --region=europe-west1 \
    --to-latest \
    --quiet

# Force specific revision
gcloud run services update-traffic streaming-stt-service \
    --region=europe-west1 \
    --to-revisions=REVISION_NAME=100 \
    --quiet
```

---

## 📊 Success Criteria

### Must Have (Iteration 2 Completion)
- [ ] Blue-green deployment working
- [ ] Zero-downtime deployments verified
- [ ] Automatic rollback on failures
- [ ] Health checks prevent bad deployments
- [ ] All test scripts passing

### Nice to Have (Future Iterations)
- [ ] Canary deployments with gradual rollout
- [ ] A/B testing support
- [ ] Deployment metrics and monitoring
- [ ] Slack/email notifications

---

## 📅 Timeline

**Total Estimated Time**: 4-5 hours

1. **Hour 1**: Script consolidation and cleanup
2. **Hour 2-3**: Blue-green implementation and testing
3. **Hour 4**: Test script creation and validation
4. **Hour 5**: Documentation and final cleanup

---

## 🎯 Next Steps After Iteration 2

Once Iteration 2 is complete, proceed to:
1. **Iteration 3**: Comprehensive testing suite
2. **Iteration 4**: Terraform infrastructure as code
3. **Iteration 5**: GitHub Actions CI/CD
4. **Iteration 6**: Staging environment

---

**Note**: This plan prioritizes stability and zero-downtime deployments. The cleanup strategy ensures no confusion between scripts while maintaining backward compatibility during the transition period.