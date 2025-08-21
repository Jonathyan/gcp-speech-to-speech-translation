#!/bin/bash
# setup-devops-venv.sh - Setup virtual environment for DevOps tools

set -e

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_step() {
    echo -e "${BLUE}🔧 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

print_step "Setting up DevOps virtual environment..."

# Check if venv already exists
if [ -d "devops-venv" ]; then
    print_info "DevOps venv already exists, removing old one..."
    rm -rf devops-venv
fi

# Create virtual environment
print_step "Creating virtual environment..."
python3 -m venv devops-venv

# Activate and install dependencies
print_step "Installing DevOps dependencies..."
source devops-venv/bin/activate

# Install required packages for DevOps testing
pip install --upgrade pip
pip install pyyaml

# Test installation
print_step "Testing installations..."
python -c "import yaml; print('✅ PyYAML working')"

deactivate

print_success "DevOps virtual environment setup complete!"
echo ""
print_info "Usage:"
echo "  source devops-venv/bin/activate    # Activate venv"
echo "  ./test-deployment.sh               # Run tests with venv"
echo "  ./validate-system.sh               # Run validation"
echo "  deactivate                         # Exit venv"
echo ""
print_info "The test scripts will automatically use this venv if available"