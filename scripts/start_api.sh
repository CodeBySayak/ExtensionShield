#!/bin/sh
set -e

echo "🚀 Starting ExtensionShield API..."
echo "PORT: ${PORT:-8007}"
echo "SUPABASE_URL: ${SUPABASE_URL:-not set}"
echo "LLM_PROVIDER: ${LLM_PROVIDER:-not set}"

# Run migrations if Supabase is configured
if [ -n "${DB_BACKEND:-}" ] && [ "${DB_BACKEND:-}" != "supabase" ]; then
  echo "⏭️  Skipping Supabase migrations: DB_BACKEND=${DB_BACKEND}"
elif [ -n "${SUPABASE_URL:-}" ] && [ -n "${SUPABASE_SERVICE_ROLE_KEY:-}" ]; then
  echo "🔄 Running Supabase migrations..."
  python scripts/run_supabase_migrations.py || {
    echo "❌ Migration failed, but continuing startup..."
  }
else
  echo "⏭️  Skipping Supabase migrations: Supabase env not set"
fi

echo "✅ Starting uvicorn server on port ${PORT:-8007}..."
exec uvicorn extension_shield.api.main:app --host 0.0.0.0 --port "${PORT:-8007}"

