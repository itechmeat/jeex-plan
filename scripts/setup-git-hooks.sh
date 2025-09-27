#!/bin/bash

# Setup git hooks for JEEX Plan project

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔧 Setting up git hooks for JEEX Plan...${NC}"

# Ensure we're in the project root
if [ ! -f "jeex-plan.code-workspace" ]; then
    echo "❌ Please run this script from the project root directory"
    exit 1
fi

# Configure git to use GitHub hooks directory
git config core.hooksPath .github/hooks

# Create hooks directory if it doesn't exist
mkdir -p .github/hooks

# Make hooks executable (they should already exist in the repo)
if [ -f ".github/hooks/pre-commit" ]; then
    chmod +x .github/hooks/pre-commit
    echo -e "${GREEN}✅ Pre-commit hook configured and made executable${NC}"
else
    echo -e "${YELLOW}⚠️  Pre-commit hook not found in .github/hooks/pre-commit${NC}"
    echo -e "${YELLOW}This should not happen if you cloned the complete repository${NC}"
fi

echo -e "${GREEN}✅ Git hooks setup completed!${NC}"
echo -e "${YELLOW}📋 Available commands for entire project:${NC}"
echo -e "  ${GREEN}make lint${NC}          - Run all linting checks (frontend, markdown, backend)"
echo -e "  ${GREEN}make lint-fix${NC}      - Fix frontend/backend/sql lint issues"
echo -e "  ${GREEN}make frontend-lint${NC}  - Run frontend lint (ESLint + Stylelint)"
echo -e "  ${GREEN}make backend-lint${NC}   - Run backend lint (SQLFluff + Ruff)"
echo -e "  ${GREEN}make frontend-fix${NC}  - Auto-fix frontend lint issues"
echo -e "  ${GREEN}make backend-fix${NC}   - Auto-fix backend lint issues"
echo -e "  ${GREEN}make format${NC}        - Format all code (frontend + backend)"
echo -e "  ${GREEN}make check${NC}         - Run type checking (frontend + backend)"
echo -e "  ${GREEN}make docker-lint${NC}   - Docker file linting (Hadolint)"
echo -e "  ${GREEN}make security-scan${NC} - Security scanning (Checkov)"
echo -e "  ${GREEN}make pre-commit${NC}     - Run all pre-commit checks manually"
echo ""
echo -e "${YELLOW}ℹ️  The pre-commit hook will automatically run these checks before every commit.${NC}"
echo -e "${YELLOW}📋 Pre-commit checks include:${NC}"
echo -e "  📝 Frontend: JavaScript/TypeScript (Biome), CSS (Stylelint), TypeScript types"
echo -e "  🐍 Backend: Python (Ruff), Python formatting, Python types (MyPy)"
echo -e "  🐳 Infrastructure: Docker linting (Hadolint), Security scanning (Checkov)"
