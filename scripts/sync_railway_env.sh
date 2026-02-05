#!/bin/bash
# Helper script to set Railway environment variables from local .env files
# This script reads your local .env files and sets them in Railway

set -e

echo "🔧 Setting Railway Environment Variables from Local .env Files"
echo "=============================================================="
echo ""

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found. Install it first:"
    echo "   npm install -g @railway/cli"
    exit 1
fi

# Check if project is linked
if ! railway status &> /dev/null 2>&1; then
    echo "❌ Not linked to a Railway project. Run:"
    echo "   railway login"
    echo "   railway link"
    exit 1
fi

echo "📋 Reading environment variables from local files..."
echo ""

# Read backend variables from root .env
if [ ! -f .env ]; then
    echo "❌ No .env file found in project root"
    exit 1
fi

# Read frontend variables from frontend/.env
if [ ! -f frontend/.env ]; then
    echo "⚠️  Warning: No frontend/.env file found"
    echo "   Frontend Supabase variables may not be set"
fi

echo "Found environment files:"
echo "  ✅ .env (backend)"
[ -f frontend/.env ] && echo "  ✅ frontend/.env (frontend)"
echo ""

# Extract values
SUPABASE_URL=$(grep "^SUPABASE_URL=" .env | cut -d'"' -f2 | cut -d= -f2)
SUPABASE_SERVICE_ROLE_KEY=$(grep "^SUPABASE_SERVICE_ROLE_KEY=" .env | cut -d= -f2)
LLM_PROVIDER=$(grep "^LLM_PROVIDER=" .env | cut -d= -f2)
OPENAI_API_KEY=$(grep "^OPENAI_API_KEY=" .env | cut -d= -f2)
LLM_MODEL=$(grep "^LLM_MODEL=" .env | cut -d= -f2)

if [ -f frontend/.env ]; then
    VITE_SUPABASE_URL=$(grep "^VITE_SUPABASE_URL=" frontend/.env | cut -d= -f2)
    VITE_SUPABASE_ANON_KEY=$(grep "^VITE_SUPABASE_ANON_KEY=" frontend/.env | cut -d= -f2)
fi

echo "📤 Setting variables in Railway..."
echo ""
echo "This will set the following variables:"
echo "  - VITE_SUPABASE_URL"
echo "  - VITE_SUPABASE_ANON_KEY"
echo "  - SUPABASE_URL"
echo "  - SUPABASE_SERVICE_ROLE_KEY"
echo "  - LLM_PROVIDER"
echo "  - OPENAI_API_KEY"
echo "  - LLM_MODEL"
echo ""

# Check if service is linked
if ! railway status 2>&1 | grep -q "Service:"; then
    echo "⚠️  No service linked. Railway will prompt you to select/create a service."
    echo ""
fi

read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "Setting variables..."

# Set variables (Railway will handle service selection)
if [ -n "$VITE_SUPABASE_URL" ]; then
    echo "  Setting VITE_SUPABASE_URL..."
    railway variables set "VITE_SUPABASE_URL=$VITE_SUPABASE_URL" || echo "    ⚠️  Failed, try manually"
fi

if [ -n "$VITE_SUPABASE_ANON_KEY" ]; then
    echo "  Setting VITE_SUPABASE_ANON_KEY..."
    railway variables set "VITE_SUPABASE_ANON_KEY=$VITE_SUPABASE_ANON_KEY" || echo "    ⚠️  Failed, try manually"
fi

if [ -n "$SUPABASE_URL" ]; then
    echo "  Setting SUPABASE_URL..."
    railway variables set "SUPABASE_URL=$SUPABASE_URL" || echo "    ⚠️  Failed, try manually"
fi

if [ -n "$SUPABASE_SERVICE_ROLE_KEY" ]; then
    echo "  Setting SUPABASE_SERVICE_ROLE_KEY..."
    railway variables set "SUPABASE_SERVICE_ROLE_KEY=$SUPABASE_SERVICE_ROLE_KEY" || echo "    ⚠️  Failed, try manually"
fi

if [ -n "$LLM_PROVIDER" ]; then
    echo "  Setting LLM_PROVIDER..."
    railway variables set "LLM_PROVIDER=$LLM_PROVIDER" || echo "    ⚠️  Failed, try manually"
fi

if [ -n "$OPENAI_API_KEY" ]; then
    echo "  Setting OPENAI_API_KEY..."
    railway variables set "OPENAI_API_KEY=$OPENAI_API_KEY" || echo "    ⚠️  Failed, try manually"
fi

if [ -n "$LLM_MODEL" ]; then
    echo "  Setting LLM_MODEL..."
    railway variables set "LLM_MODEL=$LLM_MODEL" || echo "    ⚠️  Failed, try manually"
fi

echo ""
echo "✅ Done! Verify with:"
echo "   make deploy-check"
echo ""
echo "Then deploy with:"
echo "   make deploy"
echo ""

