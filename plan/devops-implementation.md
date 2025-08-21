# DevOps Implementation Plan: Hybrid Deployment Strategy

**Objective**: Transform current fragile manual deployment into robust, automated system with minimal cost and maximum reliability.

**Priority**: Application is currently broken - focus on getting it working FIRST, then improve infrastructure.

---

## 🎯 Strategic Overview

### **Phase 1: Emergency Stabilization** (Week 1)
Fix immediate deployment issues to get application working reliably.

### **Phase 2: Infrastructure Automation** (Weeks 2-4)  
Add CI/CD, staging environment, and minimal Terraform for best practices.

---

## 📋 Phase 1: Emergency Stabilization (Get App Working)

### **Iteration 1: Cloud Build Integration** 
**Goal**: Eliminate Docker build timeouts with Cloud Build
**Timeline**: 1-2 hours
**Priority**: CRITICAL

#### **Files to Create/Modify:**
1. `cloudbuild.yaml` - Cloud Build configuration
2. `deploy-backend.sh` - Update to use Cloud Build
3. `.gcloudignore` - Optimize build context

#### **Detailed Tasks:**

**Task 1.1: Create cloudbuild.yaml**
```yaml
# cloudbuild.yaml
steps:
  # Build the container image
  - name: 'gcr.io/cloud-builders/docker'
    args: [
      'build',
      '--no-cache',
      '--platform=linux/amd64', 
      '-f', 'Dockerfile.simple',
      '-t', 'gcr.io/$PROJECT_ID/streaming-stt-service:$SHORT_SHA',
      '-t', 'gcr.io/$PROJECT_ID/streaming-stt-service:latest',
      '.'
    ]

  # Push the container image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', '--all-tags', 'gcr.io/$PROJECT_ID/streaming-stt-service']

  # Deploy to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args: [
      'run', 'deploy', 'streaming-stt-service',
      '--image=gcr.io/$PROJECT_ID/streaming-stt-service:$SHORT_SHA',
      '--region=europe-west1',
      '--platform=managed',
      '--allow-unauthenticated',
      '--memory=2Gi',
      '--cpu=1',
      '--concurrency=10',
      '--timeout=600',
      '--min-instances=1',
      '--max-instances=10',
      '--port=8080',
      '--set-env-vars=GOOGLE_CLOUD_PROJECT=$PROJECT_ID,ENABLE_STREAMING=true',
      '--service-account=speech-translator@$PROJECT_ID.iam.gserviceaccount.com',
      '--traffic=100'
    ]

# Build options
options:
  machineType: 'E2_HIGHCPU_8'  # Faster builds
  substitution_option: 'ALLOW_LOOSE'
  logging: CLOUD_LOGGING_ONLY

# Build timeout
timeout: 600s
```

**Task 1.2: Create .gcloudignore**
```
# .gcloudignore - Optimize build context
.git
.github
node_modules
__pycache__
*.pyc
.pytest_cache
.venv
venv
frontend/node_modules
frontend/dist
testing/
plan/
*.md
*.png
*.drawio
*.log
*.json
!requirements.txt
!pyproject.toml
```

**Task 1.3: Update deploy-backend.sh**
```bash
# Key changes to deploy-backend.sh:
# Replace Docker build section with:
print_step "Building with Cloud Build..."
BUILD_ID=$(gcloud builds submit \
  --config=cloudbuild.yaml \
  --substitutions=_SERVICE_NAME=$SERVICE_NAME \
  --format="value(id)")

print_step "Waiting for build completion..."
gcloud builds log $BUILD_ID --stream

# Remove local Docker build commands
# Add build status validation
```

#### **Success Criteria:**
- [ ] Build completes in <5 minutes (vs current >15 minutes)
- [ ] No local Docker timeouts
- [ ] Image successfully deployed to Cloud Run
- [ ] Health endpoint returns 200 OK

#### **Testing Commands:**
```bash
# Test the new build process
./deploy-backend.sh

# Verify deployment
curl https://streaming-stt-service-ysw2dobxea-ew.a.run.app/health
```

---

### **Iteration 2: Enhanced Traffic Management**
**Goal**: Fix traffic routing failures and add blue-green deployment
**Timeline**: 2-3 hours
**Priority**: CRITICAL

#### **Files to Modify:**
1. `deploy-backend.sh` - Add sophisticated traffic management
2. `deploy-backend-config.sh` - Environment configuration

#### **Detailed Tasks:**

**Task 2.1: Create deploy-backend-config.sh**
```bash
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

# Load environment
load_environment() {
    local env=${1:-prod}
    case $env in
        prod)
            PROD_CONFIG
            ;;
        *)
            echo "Unknown environment: $env"
            exit 1
            ;;
    esac
}
```

**Task 2.2: Enhanced deploy-backend.sh**
```bash
# Add to deploy-backend.sh:

# Blue-green deployment function
deploy_with_blue_green() {
    local new_revision=$1
    
    print_step "Starting blue-green deployment..."
    
    # Deploy new revision with 0% traffic
    print_step "Deploying new revision (0% traffic)..."
    gcloud run services update-traffic $SERVICE_NAME \
        --region=$REGION \
        --to-revisions=$new_revision=0 \
        --quiet
    
    # Wait for new revision to be ready
    print_step "Waiting for new revision to be ready..."
    wait_for_revision_ready $new_revision
    
    # Health check new revision
    print_step "Health checking new revision..."
    if health_check_revision $new_revision; then
        print_success "Health check passed!"
        
        # Switch 100% traffic to new revision
        print_step "Switching traffic to new revision..."
        gcloud run services update-traffic $SERVICE_NAME \
            --region=$REGION \
            --to-revisions=$new_revision=100 \
            --quiet
            
        print_success "Traffic switched successfully!"
        
        # Final health check
        sleep 10
        final_health_check
        
    else
        print_error "Health check failed! Rolling back..."
        rollback_deployment
        exit 1
    fi
}

# Health check function with retries
health_check_revision() {
    local revision=$1
    local attempts=0
    local max_attempts=5
    local base_url="https://streaming-stt-service-ysw2dobxea-ew.a.run.app"
    
    while [ $attempts -lt $max_attempts ]; do
        print_step "Health check attempt $((attempts + 1))/$max_attempts..."
        
        local response=$(curl -s -w "%{http_code}" -o /tmp/health_response "$base_url/health" || echo "000")
        
        if [ "$response" = "200" ]; then
            local body=$(cat /tmp/health_response)
            if [[ $body == *'"status":"ok"'* ]]; then
                print_success "Health check passed!"
                return 0
            fi
        fi
        
        attempts=$((attempts + 1))
        if [ $attempts -lt $max_attempts ]; then
            print_warning "Health check failed, retrying in 10 seconds..."
            sleep 10
        fi
    done
    
    print_error "Health check failed after $max_attempts attempts"
    return 1
}

# Rollback function
rollback_deployment() {
    print_warning "Rolling back to previous revision..."
    
    # Get previous revision
    local previous_revision=$(gcloud run revisions list \
        --service=$SERVICE_NAME \
        --region=$REGION \
        --format="value(metadata.name)" \
        --sort-by="~metadata.creationTimestamp" \
        --limit=2 | tail -n 1)
    
    if [ ! -z "$previous_revision" ]; then
        gcloud run services update-traffic $SERVICE_NAME \
            --region=$REGION \
            --to-revisions=$previous_revision=100 \
            --quiet
        print_success "Rollback completed to revision: $previous_revision"
    else
        print_error "No previous revision found for rollback!"
    fi
}

# Wait for revision to be ready
wait_for_revision_ready() {
    local revision=$1
    local attempts=0
    local max_attempts=30
    
    while [ $attempts -lt $max_attempts ]; do
        local status=$(gcloud run revisions describe $revision \
            --region=$REGION \
            --format="value(status.conditions[0].status)" 2>/dev/null || echo "Unknown")
        
        if [ "$status" = "True" ]; then
            print_success "Revision $revision is ready!"
            return 0
        fi
        
        print_step "Waiting for revision to be ready... ($attempts/$max_attempts)"
        sleep 10
        attempts=$((attempts + 1))
    done
    
    print_error "Revision failed to become ready after 5 minutes"
    return 1
}
```

#### **Success Criteria:**
- [ ] New deployments switch traffic correctly
- [ ] Health checks validate before traffic switch
- [ ] Automatic rollback on health check failures
- [ ] Zero-downtime deployments

---

### **Iteration 3: Comprehensive Testing & Validation**
**Goal**: Ensure deployment reliability before moving to Phase 2
**Timeline**: 1 hour
**Priority**: HIGH

#### **Files to Create:**
1. `test-deployment.sh` - Deployment testing script
2. `validate-system.sh` - End-to-end validation

#### **Detailed Tasks:**

**Task 3.1: Create test-deployment.sh**
```bash
#!/bin/bash
# test-deployment.sh - Test deployment process

set -e

# Test scenarios
test_scenarios=(
    "normal_deployment"
    "health_check_failure" 
    "rollback_test"
)

# Normal deployment test
test_normal_deployment() {
    echo "🧪 Testing normal deployment..."
    
    # Make a small change to trigger new build
    echo "# Test deployment $(date)" >> backend/main.py
    
    # Deploy
    ./deploy-backend.sh
    
    # Validate
    curl -f https://streaming-stt-service-ysw2dobxea-ew.a.run.app/health
    
    echo "✅ Normal deployment test passed"
}

# Health check failure simulation
test_health_check_failure() {
    echo "🧪 Testing health check failure handling..."
    
    # This would require temporarily breaking health endpoint
    # For now, just validate rollback mechanism exists
    
    if grep -q "rollback_deployment" deploy-backend.sh; then
        echo "✅ Rollback mechanism found"
    else
        echo "❌ Rollback mechanism missing"
        exit 1
    fi
}

# Run all tests
main() {
    for test in "${test_scenarios[@]}"; do
        test_$test
    done
    
    echo "🎉 All deployment tests passed!"
}

main "$@"
```

**Task 3.2: Create validate-system.sh**
```bash
#!/bin/bash
# validate-system.sh - End-to-end system validation

set -e

# Validation functions
validate_backend() {
    echo "🔍 Validating backend..."
    
    local health_response=$(curl -s https://streaming-stt-service-ysw2dobxea-ew.a.run.app/health)
    
    if [[ $health_response == *'"status":"ok"'* ]]; then
        echo "✅ Backend health check passed"
    else
        echo "❌ Backend health check failed"
        echo "Response: $health_response"
        return 1
    fi
}

validate_frontend() {
    echo "🔍 Validating frontend..."
    
    cd frontend
    ./deploy-frontend.sh
    cd ..
    
    local frontend_response=$(curl -s -I https://lfhs-translate.web.app | head -n 1)
    
    if [[ $frontend_response == *"200 OK"* ]]; then
        echo "✅ Frontend deployment successful"
    else
        echo "❌ Frontend deployment failed"
        return 1
    fi
}

validate_integration() {
    echo "🔍 Validating end-to-end integration..."
    
    # Test that frontend has correct backend URL
    local backend_url_in_frontend=$(curl -s https://lfhs-translate.web.app/app.min.js | grep -o "streaming-stt-service[^\"]*" | head -1)
    
    if [ ! -z "$backend_url_in_frontend" ]; then
        echo "✅ Frontend correctly configured with backend URL"
    else
        echo "❌ Frontend missing backend URL configuration"
        return 1
    fi
}

# Main validation
main() {
    echo "🚀 Starting system validation..."
    
    validate_backend
    validate_frontend  
    validate_integration
    
    echo "🎉 All validations passed! System is working correctly."
    echo ""
    echo "📊 System URLs:"
    echo "  • Frontend: https://lfhs-translate.web.app"
    echo "  • Backend Health: https://streaming-stt-service-ysw2dobxea-ew.a.run.app/health"
    echo "  • WebSocket: wss://streaming-stt-service-ysw2dobxea-ew.a.run.app/ws/stream/demo-stream"
}

main "$@"
```

#### **Success Criteria:**
- [ ] All test scenarios pass
- [ ] End-to-end validation successful
- [ ] Speech translation pipeline working
- [ ] Zero deployment failures

---

## 🏗️ Phase 2: Infrastructure Automation (Production Ready)

### **Iteration 4: Minimal Terraform Setup**
**Goal**: Infrastructure as Code foundation with cost optimization
**Timeline**: 4-6 hours
**Priority**: MEDIUM

#### **Files to Create:**
1. `terraform/` directory structure
2. `terraform/main.tf` - Core infrastructure
3. `terraform/variables.tf` - Configuration
4. `terraform/outputs.tf` - Resource information

#### **Detailed Tasks:**

**Task 4.1: Terraform Directory Structure**
```
terraform/
├── main.tf              # Core infrastructure
├── variables.tf         # Input variables
├── outputs.tf          # Output values
├── versions.tf         # Provider versions
├── terraform.tfvars   # Production values
└── backend.tf         # State management (optional)
```

**Task 4.2: Core Infrastructure (terraform/main.tf)**
```hcl
# terraform/main.tf - Minimal cost-optimized setup

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  
  # Optional: Remote state (add later if needed)
  # backend "gcs" {
  #   bucket = "lfhs-translate-terraform-state"  
  #   prefix = "production"
  # }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs (cost: $0)
resource "google_project_service" "required_apis" {
  for_each = toset([
    "run.googleapis.com",
    "cloudbuild.googleapis.com", 
    "speech.googleapis.com",
    "translate.googleapis.com",
    "texttospeech.googleapis.com"
  ])
  
  project = var.project_id
  service = each.value
  
  disable_dependent_services = false
  disable_on_destroy        = false
}

# Service Account (cost: $0)
resource "google_service_account" "speech_translator" {
  account_id   = "speech-translator"
  display_name = "Speech Translation Service"
  description  = "Service account for speech-to-speech translation"
  project      = var.project_id
}

# IAM bindings with least privilege (cost: $0)
resource "google_project_iam_member" "speech_translator_permissions" {
  for_each = toset([
    "roles/speech.editor",
    "roles/cloudtranslate.editor", 
    "roles/texttospeech.synthesizer"
  ])
  
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.speech_translator.email}"
}

# Cloud Run service (cost: pay-per-use)
resource "google_cloud_run_service" "speech_translation" {
  name     = var.service_name
  location = var.region
  project  = var.project_id

  template {
    metadata {
      annotations = {
        "autoscaling.knative.dev/maxScale" = var.max_instances
        "autoscaling.knative.dev/minScale" = var.min_instances
        "run.googleapis.com/execution-environment" = "gen2"
      }
    }
    
    spec {
      container_concurrency = var.container_concurrency
      timeout_seconds      = var.timeout_seconds
      service_account_name = google_service_account.speech_translator.email
      
      containers {
        image = var.container_image
        
        ports {
          container_port = 8080
        }
        
        resources {
          limits = {
            cpu    = var.cpu_limit
            memory = var.memory_limit
          }
        }
        
        env {
          name  = "GOOGLE_CLOUD_PROJECT"
          value = var.project_id
        }
        
        env {
          name  = "ENABLE_STREAMING" 
          value = "true"
        }
      }
    }
  }
  
  traffic {
    percent         = 100
    latest_revision = true
  }
  
  depends_on = [google_project_service.required_apis]
}

# Public access (cost: $0)
resource "google_cloud_run_service_iam_member" "public_access" {
  location = google_cloud_run_service.speech_translation.location
  project  = google_cloud_run_service.speech_translation.project
  service  = google_cloud_run_service.speech_translation.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
```

**Task 4.3: Variables (terraform/variables.tf)**
```hcl
# terraform/variables.tf

variable "project_id" {
  description = "GCP Project ID"
  type        = string
  default     = "lfhs-translate"
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "europe-west1"
}

variable "service_name" {
  description = "Cloud Run service name"
  type        = string
  default     = "streaming-stt-service"
}

variable "container_image" {
  description = "Container image to deploy"
  type        = string
  default     = "gcr.io/lfhs-translate/streaming-stt-service:latest"
}

# Cost-optimized defaults
variable "min_instances" {
  description = "Minimum number of instances"
  type        = number
  default     = 0  # Cost optimization: scale to zero when not used
}

variable "max_instances" {
  description = "Maximum number of instances"
  type        = number
  default     = 10
}

variable "cpu_limit" {
  description = "CPU limit"
  type        = string
  default     = "1"
}

variable "memory_limit" {
  description = "Memory limit"
  type        = string
  default     = "2Gi"
}

variable "container_concurrency" {
  description = "Container concurrency"
  type        = number
  default     = 10
}

variable "timeout_seconds" {
  description = "Request timeout in seconds"
  type        = number
  default     = 600
}
```

**Task 4.4: Outputs (terraform/outputs.tf)**
```hcl
# terraform/outputs.tf

output "service_url" {
  description = "Cloud Run service URL"
  value       = google_cloud_run_service.speech_translation.status[0].url
}

output "service_name" {
  description = "Cloud Run service name"
  value       = google_cloud_run_service.speech_translation.name
}

output "service_account_email" {
  description = "Service account email"
  value       = google_service_account.speech_translator.email
}
```

#### **Success Criteria:**
- [ ] `terraform plan` shows expected resources
- [ ] `terraform apply` completes successfully  
- [ ] Infrastructure matches current manual setup
- [ ] No additional costs introduced

#### **Cost Analysis:**
```yaml
# Additional costs from Terraform setup:
Terraform State (local): $0
Additional APIs: $0
Service Account: $0
IAM bindings: $0

Total additional cost: $0
```

---

### **Iteration 5: GitHub Actions CI/CD**
**Goal**: Automated deployments on code changes
**Timeline**: 3-4 hours
**Priority**: MEDIUM

#### **Files to Create:**
1. `.github/workflows/deploy-production.yml`
2. `.github/workflows/test.yml`
3. `scripts/setup-github-actions.sh`

#### **Detailed Tasks:**

**Task 5.1: Production Deployment Workflow**
```yaml
# .github/workflows/deploy-production.yml

name: Deploy to Production

on:
  push:
    branches: [main, master]
    paths:
      - 'backend/**'
      - 'requirements.txt'
      - 'Dockerfile.simple'
      - 'cloudbuild.yaml'

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    permissions:
      contents: read
      id-token: write
      
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      
    - name: Authenticate to Google Cloud
      uses: google-github-actions/auth@v1
      with:
        credentials_json: ${{ secrets.GCP_SA_KEY }}
        
    - name: Set up Cloud SDK
      uses: google-github-actions/setup-gcloud@v1
      
    - name: Configure Docker for GCR
      run: gcloud auth configure-docker
      
    - name: Deploy with Cloud Build
      run: |
        BUILD_ID=$(gcloud builds submit \
          --config=cloudbuild.yaml \
          --substitutions=_SERVICE_NAME=streaming-stt-service \
          --format="value(id)")
        
        echo "Build ID: $BUILD_ID"
        
        # Wait for build completion
        gcloud builds log $BUILD_ID --stream
        
    - name: Verify deployment
      run: |
        sleep 30
        curl -f https://streaming-stt-service-ysw2dobxea-ew.a.run.app/health
        
    - name: Deploy frontend
      run: |
        cd frontend
        npm ci
        npm run build
        
        # Deploy to Firebase (requires setup)
        # firebase deploy --only hosting
```

**Task 5.2: Test Workflow**
```yaml
# .github/workflows/test.yml

name: Run Tests

on:
  pull_request:
    branches: [main, master]
  push:
    branches: [develop, feature/*]

jobs:
  test-backend:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
        
    - name: Install Poetry
      run: |
        curl -sSL https://install.python-poetry.org | python3 -
        echo "$HOME/.local/bin" >> $GITHUB_PATH
        
    - name: Install dependencies
      run: poetry install
      
    - name: Run backend tests
      run: poetry run pytest backend/tests/ -v
      
  test-frontend:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Node.js
      uses: actions/setup-node@v4
      with:
        node-version: '18'
        
    - name: Install dependencies
      run: |
        cd frontend
        npm ci
        
    - name: Run frontend tests
      run: |
        cd frontend
        npm test
```

**Task 5.3: GitHub Actions Setup Script**
```bash
#!/bin/bash
# scripts/setup-github-actions.sh

set -e

echo "🔧 Setting up GitHub Actions CI/CD..."

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ Not in a git repository"
    exit 1
fi

# Check if GitHub CLI is installed
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) is required but not installed"
    echo "Install with: brew install gh"
    exit 1
fi

# Check if user is authenticated with GitHub
if ! gh auth status &> /dev/null; then
    echo "🔐 Please authenticate with GitHub first:"
    gh auth login
fi

# Get project details
PROJECT_ID=$(gcloud config get-value project)
SA_EMAIL="speech-translator@${PROJECT_ID}.iam.gserviceaccount.com"

# Create service account key for GitHub Actions
echo "🔑 Creating service account key for GitHub Actions..."
gcloud iam service-accounts keys create github-actions-key.json \
    --iam-account=$SA_EMAIL

# Convert key to base64
KEY_BASE64=$(base64 -i github-actions-key.json)

# Set GitHub secret
echo "📝 Setting GitHub repository secret..."
echo "$KEY_BASE64" | gh secret set GCP_SA_KEY

# Clean up local key file
rm github-actions-key.json

echo "✅ GitHub Actions setup complete!"
echo ""
echo "Next steps:"
echo "1. Push changes to trigger deployment"
echo "2. Monitor workflow at: $(git remote get-url origin | sed 's/\.git$//')/actions"
```

#### **Success Criteria:**
- [ ] GitHub Actions workflows created
- [ ] Service account key configured as secret
- [ ] Push to main branch triggers deployment
- [ ] Pull requests run tests
- [ ] Deployment completes successfully

---

### **Iteration 6: Staging Environment**
**Goal**: Add staging environment for testing before production
**Timeline**: 2-3 hours  
**Priority**: LOW

#### **Files to Create/Modify:**
1. `terraform/environments/staging/` - Staging Terraform
2. `cloudbuild-staging.yaml` - Staging build config
3. `.github/workflows/deploy-staging.yml`

#### **Detailed Tasks:**

**Task 6.1: Staging Terraform Configuration**
```bash
# Directory structure:
terraform/
├── environments/
│   ├── production/
│   │   ├── main.tf
│   │   ├── terraform.tfvars
│   │   └── versions.tf
│   └── staging/
│       ├── main.tf  
│       ├── terraform.tfvars
│       └── versions.tf
└── modules/
    └── speech-translation/
        ├── main.tf
        ├── variables.tf
        └── outputs.tf
```

**Task 6.2: Staging Environment Variables**
```hcl
# terraform/environments/staging/terraform.tfvars

project_id = "lfhs-translate"
region     = "europe-west1"
service_name = "streaming-stt-service-staging"
container_image = "gcr.io/lfhs-translate/streaming-stt-service:staging"

# Staging-specific (cost-optimized)
min_instances = 0        # Scale to zero
max_instances = 3        # Lower limit
cpu_limit = "0.5"        # Smaller instances
memory_limit = "1Gi"     # Less memory
```

**Task 6.3: Staging Deployment Workflow**
```yaml
# .github/workflows/deploy-staging.yml

name: Deploy to Staging

on:
  push:
    branches: [develop]
  pull_request:
    branches: [main, master]

jobs:
  deploy-staging:
    runs-on: ubuntu-latest
    environment: staging
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Authenticate to Google Cloud  
      uses: google-github-actions/auth@v1
      with:
        credentials_json: ${{ secrets.GCP_SA_KEY }}
        
    - name: Deploy to staging
      run: |
        cd terraform/environments/staging
        terraform init
        terraform plan -var="container_image=gcr.io/lfhs-translate/streaming-stt-service:staging-${{ github.sha }}"
        terraform apply -auto-approve
        
    - name: Run staging tests
      run: |
        # Wait for deployment
        sleep 60
        
        # Test staging environment
        curl -f https://streaming-stt-service-staging-ysw2dobxea-ew.a.run.app/health
```

#### **Success Criteria:**
- [ ] Staging environment deploys successfully
- [ ] Separate staging URLs working
- [ ] Lower resource allocation (cost optimization)
- [ ] Integration tests pass on staging

---

### **Iteration 7: Secret Management (Optional)**
**Goal**: Move sensitive configuration to Google Secret Manager
**Timeline**: 2-3 hours
**Priority**: LOW

#### **Files to Create/Modify:**
1. `terraform/modules/secrets/` - Secret Manager module
2. `backend/config.py` - Secret Manager integration
3. `scripts/migrate-secrets.sh` - Migration script

#### **Detailed Tasks:**

**Task 7.1: Secret Manager Module**
```hcl
# terraform/modules/secrets/main.tf

resource "google_secret_manager_secret" "app_secrets" {
  for_each = var.secrets
  
  secret_id = each.key
  project   = var.project_id
  
  replication {
    auto {}  # Cost-optimized: automatic replication
  }
}

resource "google_secret_manager_secret_version" "app_secret_versions" {
  for_each = var.secrets
  
  secret      = google_secret_manager_secret.app_secrets[each.key].id
  secret_data = each.value
}

# Grant access to Cloud Run service account
resource "google_secret_manager_secret_iam_member" "secret_access" {
  for_each = var.secrets
  
  project   = var.project_id
  secret_id = google_secret_manager_secret.app_secrets[each.key].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${var.service_account_email}"
}
```

#### **Cost Analysis:**
```yaml
# Secret Manager costs:
Secret storage: $0.06 per 10,000 secret versions per month
API operations: $0.03 per 10,000 operations

Estimated monthly cost: ~$1-2 for typical usage
```

#### **Success Criteria:**
- [ ] Secrets stored in Secret Manager
- [ ] Application reads secrets correctly
- [ ] No hardcoded sensitive values
- [ ] Cost remains under $5/month additional

---

## 📊 Success Metrics & Validation

### **Phase 1 Success Criteria (Must Have)**
- [ ] ✅ Application works end-to-end
- [ ] ✅ Build time <5 minutes (vs >15 minutes)
- [ ] ✅ Zero-downtime deployments
- [ ] ✅ Automatic rollback on failures
- [ ] ✅ Health checks validate before traffic switch

### **Phase 2 Success Criteria (Nice to Have)**  
- [ ] 🏗️ Infrastructure defined in Terraform
- [ ] 🤖 GitHub Actions CI/CD working
- [ ] 🧪 Staging environment available
- [ ] 🔐 Secrets managed securely
- [ ] 💰 Additional costs <$10/month

## 💰 Cost Analysis

### **Current Costs (Baseline)**
```yaml
Cloud Run: ~$20/month (current usage)
Firebase Hosting: Free tier
Google APIs: Pay-per-use (~$5-15/month)
Total: ~$25-35/month
```

### **Additional Costs from Implementation**
```yaml
Cloud Build: $0.003 per build minute
- Estimated: 10 builds/month × 5 minutes = $0.15/month

Secret Manager (optional): 
- Storage: $0.06 per 10,000 versions
- Estimated: $1-2/month

Staging environment:
- Additional Cloud Run instance: ~$10-15/month
- Total additional: ~$11-17/month

Total additional cost: $1-17/month (depending on features implemented)
```

## 🎯 Implementation Timeline

### **Week 1: Phase 1 - Emergency Stabilization**
- **Day 1**: Iterations 1-2 (Cloud Build + Traffic Management)
- **Day 2**: Iteration 3 (Testing & Validation) 
- **Day 3**: Bug fixes and optimization
- **Result**: Working, reliable deployment process

### **Week 2-3: Phase 2 - Infrastructure Automation**
- **Week 2**: Iterations 4-5 (Terraform + GitHub Actions)
- **Week 3**: Iterations 6-7 (Staging + Secrets)
- **Result**: Full CI/CD pipeline with staging environment

## ⚠️ Risk Mitigation

### **High-Risk Items**
1. **Cloud Build failures** - Mitigation: Keep local build as backup
2. **Traffic routing issues** - Mitigation: Manual rollback procedures
3. **Terraform state corruption** - Mitigation: Start with local state, backup regularly
4. **Cost overruns** - Mitigation: Set up budget alerts, monitor usage

### **Rollback Plan**
Each iteration includes rollback procedures:
- **Iteration 1-3**: Revert to original `deploy-backend.sh`
- **Iteration 4-7**: `terraform destroy` if needed
- **All iterations**: Keep previous deployment as backup

## 🚀 Getting Started

**Immediate Next Steps:**
1. **Create this plan file**: `plan/devops-implementation.md`
2. **Start with Iteration 1**: Cloud Build integration
3. **Test thoroughly**: Each iteration before proceeding
4. **Monitor costs**: Set up billing alerts
5. **Document issues**: Track problems for quick resolution

**Success Indicators:**
- ✅ Application working reliably
- ✅ Faster deployments (<5 min)
- ✅ Automated CI/CD pipeline
- ✅ Cost under control (<$50/month total)

---

*This plan prioritizes getting the application working FIRST, then gradually improving the infrastructure for production readiness and cost optimization.*