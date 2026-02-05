# Production Deployment

This guide covers production deployment basics and the Supabase migration flow.

## Key Environment Variables

Required for Supabase-backed production:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY` (server-side only)
- `DATABASE_URL` (or `SUPABASE_DB_URL`)

Optional:

- `DB_BACKEND=supabase` (auto-detected if Supabase vars are set)
- `PORT` (defaults to 8007)

## Migrations (Auto-run on Deploy)

Production startup runs migrations **before** the API server when:

- `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` are set, and
- `DB_BACKEND` is **not** `sqlite`

If migrations fail, startup exits non-zero so deploy fails fast.

The runner is:

- `scripts/run_supabase_migrations.py`

It applies SQL files in `docs/supabase_migrations/` in order and tracks
applied migrations in `public.schema_migrations`.

You can also run it manually:

```bash
python scripts/run_supabase_migrations.py
```

See `docs/MIGRATIONS.md` for full details.

## Start Command (Production)

Container startup uses:

```
scripts/start_api.sh
```

This script conditionally runs Supabase migrations and then starts the API:

```
uvicorn extension_shield.api.main:app --host 0.0.0.0 --port ${PORT:-8007}
```

## Verify Migrations

In Supabase SQL editor:

```sql
select * from public.schema_migrations order by applied_at;
```

