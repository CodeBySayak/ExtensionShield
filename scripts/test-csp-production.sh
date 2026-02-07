#!/bin/bash

# Test CSP in Production
# Verifies CSP header is being sent by the backend

set -e

echo "🔒 Testing CSP in Production"
echo "============================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check if static/index.html exists
echo "1️⃣  Checking if production build exists..."
if [ -f "static/index.html" ]; then
    echo -e "${GREEN}✅ static/index.html exists${NC}"
else
    echo -e "${RED}❌ static/index.html NOT found${NC}"
    echo "   Run: ./scripts/setup-production-csp.sh"
    exit 1
fi
echo ""

# Check if backend is running
echo "2️⃣  Checking if backend is running..."
TEST_URL="${PROD_URL:-http://localhost:8007/}"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -L "$TEST_URL" 2>/dev/null || echo "000")

if echo "$HTTP_CODE" | grep -qE "200|301|302|303|307|308"; then
    echo -e "${GREEN}✅ Backend is running on ${TEST_URL}${NC}"
else
    echo -e "${RED}❌ Backend is NOT running on ${TEST_URL}${NC}"
    echo "   Start backend: make api"
    exit 1
fi
echo ""

# Test CSP header
echo "3️⃣  Testing CSP header..."
CSP_HEADERS=$(curl -sIL "$TEST_URL" 2>/dev/null | grep -iE "content-security-policy|content-security-policy-report-only" || echo "")

if [ -z "$CSP_HEADERS" ]; then
    echo -e "${RED}❌ CSP header NOT found!${NC}"
    echo ""
    echo "Possible issues:"
    echo "  1. Backend not in production mode (check logs for 'PROD mode')"
    echo "  2. CSP middleware not registered"
    echo "  3. HTML detection failing"
    echo ""
    echo "Check backend logs for:"
    echo "  - '✅ CSP: Production mode detected'"
    echo "  - '🔒 CSP Middleware initialized: PROD mode'"
    exit 1
fi

# Check for enforcement header
ENFORCE_HEADER=$(echo "$CSP_HEADERS" | grep -i "content-security-policy:" | grep -v "report-only" || echo "")
REPORT_ONLY_HEADER=$(echo "$CSP_HEADERS" | grep -i "content-security-policy-report-only" || echo "")

if [ -n "$ENFORCE_HEADER" ]; then
    echo -e "${GREEN}✅ CSP enforcement header found!${NC}"
    POLICY=$(echo "$ENFORCE_HEADER" | cut -d: -f2- | sed 's/^[[:space:]]*//')
    echo "   Header: Content-Security-Policy"
    echo "   Policy preview:"
    echo "$POLICY" | fold -w 80 | sed 's/^/   /'
    echo ""
    
    # Check if it's strict
    if echo "$POLICY" | grep -qi "unsafe-eval"; then
        echo -e "${RED}❌ CSP contains 'unsafe-eval' (should be strict in production)${NC}"
        exit 1
    else
        echo -e "${GREEN}✅ CSP is strict (no unsafe-eval)${NC}"
    fi
    
    # Check for unsafe-inline in script-src
    if echo "$POLICY" | grep -qi "script-src.*unsafe-inline"; then
        echo -e "${YELLOW}⚠️  CSP contains 'unsafe-inline' in script-src (should be removed in production)${NC}"
    else
        echo -e "${GREEN}✅ CSP script-src is strict (no unsafe-inline)${NC}"
    fi
fi

if [ -n "$REPORT_ONLY_HEADER" ]; then
    echo -e "${YELLOW}⚠️  Report-only header also present (testing mode)${NC}"
    POLICY=$(echo "$REPORT_ONLY_HEADER" | cut -d: -f2- | sed 's/^[[:space:]]*//')
    echo "   Header: Content-Security-Policy-Report-Only"
    echo -e "${BLUE}   ℹ️  Report-only mode: violations logged but not blocked${NC}"
fi

echo ""
echo -e "${GREEN}✅ CSP is working correctly in production!${NC}"
echo ""

