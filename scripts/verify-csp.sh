#!/bin/bash

# CSP Verification Script
# Checks if CSP is properly configured in dev and production
# 
# IMPORTANT: In production, the HTTP response header is the source of truth for CSP enforcement.
# Meta tags are fallback only (for static hosting without header support).

set -e

echo "🔒 CSP Verification Script"
echo "=========================="
echo ""
echo "⚠️  IMPORTANT: In production, HTTP response headers are the source of truth for CSP."
echo "   Meta tags are fallback only for static hosting scenarios."
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check 1: Dev mode - Check if Vite plugin injects CSP
echo "1️⃣  Checking Dev Mode CSP (Vite plugin)..."
if [ -f "frontend/vite.config.js" ]; then
    if grep -q "inject-csp-meta" frontend/vite.config.js; then
        echo -e "${GREEN}✅ Vite CSP plugin found${NC}"
    else
        echo -e "${RED}❌ Vite CSP plugin not found${NC}"
    fi
else
    echo -e "${RED}❌ vite.config.js not found${NC}"
fi
echo ""

# Check 2: Production build - Check if CSP meta tag is injected (fallback only)
echo "2️⃣  Checking Production Build CSP (meta tag - fallback only)..."
if [ -f "frontend/dist/index.html" ]; then
    if grep -qi "content-security-policy" frontend/dist/index.html; then
        echo -e "${GREEN}✅ CSP meta tag found in production build (fallback)${NC}"
        echo "   CSP content:"
        grep -i "content-security-policy" frontend/dist/index.html | head -1 | sed 's/^/   /'
        
        # Check if it's strict (no unsafe-eval)
        if grep -qi "content-security-policy" frontend/dist/index.html | grep -q "unsafe-eval"; then
            echo -e "${YELLOW}⚠️  WARNING: Production CSP meta tag contains 'unsafe-eval' (should be strict)${NC}"
        else
            echo -e "${GREEN}✅ Production CSP meta tag is strict (no unsafe-eval)${NC}"
        fi
        echo -e "${BLUE}   ℹ️  Note: Meta tag is fallback. HTTP header (if present) takes precedence.${NC}"
    else
        echo -e "${YELLOW}⚠️  CSP meta tag NOT found in production build${NC}"
        echo "   Run: cd frontend && npm run build"
        echo -e "${BLUE}   ℹ️  This is OK if HTTP headers are set by hosting provider.${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Production build not found. Run: cd frontend && npm run build${NC}"
fi
echo ""

# Check 3: Backend middleware - Check if CSP middleware exists
echo "3️⃣  Checking Backend CSP Middleware..."
if [ -f "src/extension_shield/api/csp_middleware.py" ]; then
    echo -e "${GREEN}✅ CSP middleware file exists${NC}"
    
    if grep -q "CSPMiddleware" src/extension_shield/api/main.py; then
        echo -e "${GREEN}✅ CSP middleware is registered in main.py${NC}"
    else
        echo -e "${RED}❌ CSP middleware NOT registered in main.py${NC}"
    fi
else
    echo -e "${RED}❌ CSP middleware file not found${NC}"
fi
echo ""

# Check 4: Verify CSP strings match
echo "4️⃣  Verifying CSP Policy Requirements..."
echo "   Production CSP should:"
echo "   - ✅ NOT contain 'unsafe-eval'"
echo "   - ✅ NOT contain 'unsafe-inline' in script-src"
echo "   - ✅ Contain 'unsafe-inline' in style-src (only if required by libraries)"
echo "   - ✅ Contain Supabase domains in connect-src and frame-src"
echo ""

# Check 5: Test CSP header on running server (optional)
echo "5️⃣  Testing CSP Header on Server (optional)..."
echo "   This checks if CSP header is actually being sent by the server."
echo ""

# Determine URL to test
TEST_URL="${PROD_URL:-http://localhost:8007/}"

if command -v curl &> /dev/null; then
    # Test if server is reachable (follow redirects)
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -L "$TEST_URL" 2>/dev/null || echo "000")
    
    if echo "$HTTP_CODE" | grep -qE "200|301|302|303|307|308"; then
        echo -e "${BLUE}   Server appears to be running on ${TEST_URL}${NC}"
        echo "   Testing CSP headers (following redirects)..."
        
        # Get all headers, follow redirects, check for both CSP headers
        CSP_HEADERS=$(curl -sIL "$TEST_URL" 2>/dev/null | grep -iE "content-security-policy|content-security-policy-report-only" || echo "")
        
        if [ -n "$CSP_HEADERS" ]; then
            # Check for enforcement header
            ENFORCE_HEADER=$(echo "$CSP_HEADERS" | grep -i "content-security-policy:" | grep -v "report-only" || echo "")
            REPORT_ONLY_HEADER=$(echo "$CSP_HEADERS" | grep -i "content-security-policy-report-only" || echo "")
            
            if [ -n "$ENFORCE_HEADER" ]; then
                echo -e "${GREEN}✅ CSP enforcement header found!${NC}"
                POLICY=$(echo "$ENFORCE_HEADER" | cut -d: -f2- | sed 's/^[[:space:]]*//')
                POLICY_PREVIEW=$(echo "$POLICY" | cut -c1-200)
                echo "   Header: Content-Security-Policy"
                echo "   Policy (first 200 chars): $POLICY_PREVIEW..."
                
                # Check if it's strict
                if echo "$POLICY" | grep -qi "unsafe-eval"; then
                    echo -e "${YELLOW}⚠️  WARNING: CSP header contains 'unsafe-eval' (should be strict)${NC}"
                else
                    echo -e "${GREEN}✅ CSP header is strict (no unsafe-eval)${NC}"
                fi
            fi
            
            if [ -n "$REPORT_ONLY_HEADER" ]; then
                echo -e "${YELLOW}⚠️  Report-only header found (testing mode)${NC}"
                POLICY=$(echo "$REPORT_ONLY_HEADER" | cut -d: -f2- | sed 's/^[[:space:]]*//')
                POLICY_PREVIEW=$(echo "$POLICY" | cut -c1-200)
                echo "   Header: Content-Security-Policy-Report-Only"
                echo "   Policy (first 200 chars): $POLICY_PREVIEW..."
                echo -e "${BLUE}   ℹ️  Report-only mode: violations logged but not blocked${NC}"
            fi
            
            if [ -z "$ENFORCE_HEADER" ] && [ -z "$REPORT_ONLY_HEADER" ]; then
                echo -e "${RED}❌ No CSP headers found${NC}"
            fi
        else
            echo -e "${RED}❌ CSP headers NOT found in HTTP response${NC}"
            echo "   This means CSP is NOT being enforced!"
            echo "   Check:"
            echo "   1. Is CSP middleware registered in main.py?"
            echo "   2. Is the server running in production mode?"
            echo "   3. Is static/index.html present?"
            echo "   4. If using separate frontend host, configure CSP in hosting provider"
        fi
    else
        echo -e "${YELLOW}⚠️  Server not reachable at ${TEST_URL}${NC}"
        echo "   To test CSP header:"
        echo "   1. Start server: make api"
        echo "   2. Run: curl -sIL http://localhost:8007/ | grep -iE 'content-security-policy|content-security-policy-report-only'"
        echo ""
        echo "   Or set PROD_URL environment variable:"
        echo "   PROD_URL=https://extensionshield.com/ ./scripts/verify-csp.sh"
    fi
else
    echo -e "${YELLOW}⚠️  curl not found. Install curl to test CSP headers.${NC}"
fi
echo ""

# Summary
echo "📊 Summary"
echo "=========="
echo ""
echo "To verify CSP is actually enforced in production:"
echo ""
echo -e "${BLUE}  DEFINITIVE METHOD (HTTP Header):${NC}"
echo "    curl -sIL http://localhost:8007/ | grep -iE 'content-security-policy|content-security-policy-report-only'"
echo "    OR"
echo "    curl -sIL https://extensionshield.com/ | grep -iE 'content-security-policy|content-security-policy-report-only'"
echo ""
echo "   Note: Check the HTML document response (/, index.html), not API/assets"
echo ""
echo "  If header is present → CSP is ENFORCED ✅"
echo "  If no header → CSP is NOT enforced ❌"
echo ""
echo "  Development:"
echo "    1. cd frontend && npm run dev"
echo "    2. Open http://localhost:5173"
echo "    3. Check DevTools → Elements → <head> for CSP meta tag"
echo "    4. Should see permissive CSP with 'unsafe-eval'"
echo ""
echo "  Production (FastAPI serves SPA):"
echo "    1. cd frontend && npm run build"
echo "    2. make api (or start backend server)"
echo "    3. curl -sIL http://localhost:8007/ | grep -iE 'content-security-policy|content-security-policy-report-only'"
echo "    4. Should see strict CSP header (no 'unsafe-eval')"
echo ""
echo "  Production (Separate frontend host):"
echo "    1. Deploy frontend to hosting provider"
echo "    2. curl -sIL https://extensionshield.com/ | grep -iE 'content-security-policy|content-security-policy-report-only'"
echo "    3. If no header, configure CSP in hosting provider settings"
echo ""
echo "  Test production URL:"
echo "    PROD_URL=https://extensionshield.com/ ./scripts/verify-csp.sh"
echo ""
echo "  Report-Only Mode (for testing):"
echo "    CSP_REPORT_ONLY=true make api"
echo "    Check browser console for CSP violation reports"
echo "    Note: Reports are logged to console, NOT sent to server"
echo "    (unless report-to/report-uri is configured)"
echo ""
