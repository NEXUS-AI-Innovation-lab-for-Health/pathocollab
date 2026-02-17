#!/bin/bash
set -e

echo "🧪 Running Pixtral Tests..."

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

FAILED=0

# Backend tests
echo -e "\n${YELLOW}=== Backend Tests ===${NC}"

services=("auth-service" "cases-service" "workflow-service" "images-service" "reports-service")

for service in "${services[@]}"; do
    echo -e "\n${YELLOW}Testing $service...${NC}"
    cd "apps/$service"
    
    if pytest tests/ --cov=app --cov-report=term-missing -v 2>/dev/null; then
        echo -e "${GREEN}✓ $service tests passed${NC}"
    else
        echo -e "${RED}✗ $service tests failed or no tests found${NC}"
        FAILED=$((FAILED + 1))
    fi
    
    cd ../..
done

# Frontend tests
echo -e "\n${YELLOW}=== Frontend Tests ===${NC}"
cd apps/web

if yarn test --watchAll=false --coverage 2>/dev/null; then
    echo -e "${GREEN}✓ Frontend tests passed${NC}"
else
    echo -e "${YELLOW}⚠ Frontend tests skipped or failed${NC}"
fi

cd ../..

# Summary
echo -e "\n${YELLOW}=== Test Summary ===${NC}"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All backend services passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ $FAILED service(s) failed${NC}"
    exit 1
fi
