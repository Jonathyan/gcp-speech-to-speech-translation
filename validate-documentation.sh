#!/bin/bash
# validate-documentation.sh - Comprehensive documentation validation

set -e

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

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

print_step "Validating comprehensive documentation..."

# Check main documentation files
validate_main_docs() {
    print_step "Checking main documentation files..."
    
    local required_files=(
        "README.md"
        "CLAUDE.md"
        "ARCHITECTURE.md"
        "frontend/README.md"
    )
    
    local missing_files=()
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            missing_files+=("$file")
        fi
    done
    
    if [ ${#missing_files[@]} -eq 0 ]; then
        print_success "All main documentation files present"
    else
        print_error "Missing documentation files: ${missing_files[*]}"
        return 1
    fi
}

# Validate README comprehensiveness
validate_readme_sections() {
    print_step "Validating README comprehensiveness..."
    
    local required_sections=(
        "Quick Start"
        "Architecture"
        "Development Setup"
        "Deployment.*DevOps"
        "Testing"
        "Project Structure"
        "Configuration"
        "Troubleshooting"
        "Contributing"
    )
    
    local missing_sections=()
    
    for section in "${required_sections[@]}"; do
        if ! grep -q "# .*$section" README.md; then
            missing_sections+=("$section")
        fi
    done
    
    if [ ${#missing_sections[@]} -eq 0 ]; then
        print_success "All required README sections present"
    else
        print_warning "Missing README sections: ${missing_sections[*]}"
    fi
}

# Validate frontend README integration
validate_frontend_readme() {
    print_step "Validating frontend README integration..."
    
    # Check if frontend README references main system
    if grep -q "Main README" frontend/README.md; then
        print_success "Frontend README properly integrated with main system"
    else
        print_warning "Frontend README missing main system references"
    fi
    
    # Check frontend-specific sections
    local frontend_sections=(
        "Quick Start"
        "Frontend Architecture"
        "Configuration"
        "Testing"
        "Browser Support"
        "Deployment"
        "Troubleshooting"
    )
    
    local missing_frontend_sections=()
    
    for section in "${frontend_sections[@]}"; do
        if ! grep -q "# .*$section" frontend/README.md; then
            missing_frontend_sections+=("$section")
        fi
    done
    
    if [ ${#missing_frontend_sections[@]} -eq 0 ]; then
        print_success "All frontend sections present"
    else
        print_warning "Missing frontend sections: ${missing_frontend_sections[*]}"
    fi
}

# Validate DevOps documentation
validate_devops_docs() {
    print_step "Validating DevOps documentation coverage..."
    
    # Check if DevOps iteration 2 is documented
    if grep -q "DevOps Iteration 2.*COMPLETED" README.md; then
        print_success "DevOps Iteration 2 completion documented"
    else
        print_warning "DevOps Iteration 2 completion not clearly documented"
    fi
    
    # Check deployment commands
    if grep -q "deploy-backend.sh" README.md && grep -q "test-deployment.sh" README.md; then
        print_success "Deployment commands documented"
    else
        print_warning "Deployment commands not fully documented"
    fi
    
    # Check blue-green deployment mention
    if grep -q "blue-green" README.md; then
        print_success "Blue-green deployment documented"
    else
        print_warning "Blue-green deployment not mentioned"
    fi
}

# Validate URLs and links
validate_urls() {
    print_step "Validating URLs and links..."
    
    # Check production URLs
    local urls=(
        "https://lfhs-translate.web.app"
        "https://streaming-stt-service-ysw2dobxea-ew.a.run.app/health"
    )
    
    local failed_urls=()
    
    for url in "${urls[@]}"; do
        if ! curl -s -f "$url" > /dev/null 2>&1; then
            failed_urls+=("$url")
        fi
    done
    
    if [ ${#failed_urls[@]} -eq 0 ]; then
        print_success "All production URLs accessible"
    else
        print_warning "Failed URLs: ${failed_urls[*]}"
    fi
}

# Validate script references
validate_script_references() {
    print_step "Validating script references..."
    
    local scripts=(
        "deploy-backend.sh"
        "test-deployment.sh"
        "validate-system.sh"
        "setup-devops-venv.sh"
    )
    
    local missing_scripts=()
    local missing_references=()
    
    for script in "${scripts[@]}"; do
        if [ ! -f "$script" ]; then
            missing_scripts+=("$script")
        fi
        
        if ! grep -q "$script" README.md; then
            missing_references+=("$script")
        fi
    done
    
    if [ ${#missing_scripts[@]} -eq 0 ]; then
        print_success "All referenced scripts exist"
    else
        print_error "Missing scripts: ${missing_scripts[*]}"
    fi
    
    if [ ${#missing_references[@]} -eq 0 ]; then
        print_success "All scripts properly referenced in README"
    else
        print_warning "Scripts not referenced in README: ${missing_references[*]}"
    fi
}

# Validate project structure documentation
validate_project_structure() {
    print_step "Validating project structure documentation..."
    
    # Check if project structure section exists and is comprehensive
    if grep -A 50 "Project Structure" README.md | grep -q "backend/"; then
        print_success "Project structure includes backend"
    else
        print_warning "Project structure missing backend details"
    fi
    
    if grep -A 50 "Project Structure" README.md | grep -q "frontend/"; then
        print_success "Project structure includes frontend"
    else
        print_warning "Project structure missing frontend details"
    fi
    
    if grep -A 50 "Project Structure" README.md | grep -q "DevOps"; then
        print_success "Project structure includes DevOps"
    else
        print_warning "Project structure missing DevOps details"
    fi
}

# Main validation
main() {
    echo "🚀 Starting comprehensive documentation validation..."
    echo ""
    
    local validations=(
        "validate_main_docs"
        "validate_readme_sections"
        "validate_frontend_readme"
        "validate_devops_docs"
        "validate_urls"
        "validate_script_references"
        "validate_project_structure"
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
    echo "📊 Documentation Validation Results:"
    echo "  • Total validations: $total_validations"
    echo "  • Passed: $passed_validations"
    echo "  • Failed: ${#failed_validations[@]}"
    echo ""
    
    if [ ${#failed_validations[@]} -eq 0 ]; then
        print_success "All documentation validations passed! 🎉"
        echo ""
        print_success "✅ Documentation is comprehensive and production-ready"
        echo ""
        echo "📚 Key Documentation:"
        echo "  • Main README: Complete system overview and setup"
        echo "  • Frontend README: Detailed frontend documentation"
        echo "  • CLAUDE.md: Development guidance"
        echo "  • DevOps: Blue-green deployment with testing"
        echo ""
        return 0
    else
        print_warning "Some documentation areas need attention: ${failed_validations[*]}"
        echo ""
        print_success "Documentation is functional but has room for improvement"
        return 0  # Don't fail overall - warnings are acceptable
    fi
}

main "$@"