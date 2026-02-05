# Supabase Migrations

This repo includes a migration runner so you don't need to manually apply SQL
files in the Supabase UI. It applies the SQL files in `docs/supabase_migrations/`
in order and tracks applied migrations in `public.schema_migrations`.

## How to get the Postgres connection string

In Supabase dashboard:

1. Go to **Settings → Database**
2. Under **Connection string**, copy the **URI** format

This value is used as `DATABASE_URL` or `SUPABASE_DB_URL`.

## Required environment variables

The runner validates your Supabase backend configuration and uses a direct
Postgres connection:

Required:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY` (server-side only, never in frontend)

Preferred for DB connection:

- `DATABASE_URL` (or `SUPABASE_DB_URL`)

Alternative (if you don't use a single URL):

- `PGHOST`
- `PGPORT`
- `PGDATABASE`
- `PGUSER`
- `PGPASSWORD`

## Run migrations

From the repo root:

```bash
python scripts/run_supabase_migrations.py
```

The script:

- Creates `public.schema_migrations` if it doesn't exist
- Applies files matching `^\d{3}[a-z]?_.*\.sql$`
- Stores filename + checksum in `schema_migrations`
- Is safe to run multiple times (skips already-applied migrations)

## Verify applied migrations

In Supabase SQL Editor:

```sql
select * from public.schema_migrations order by applied_at;
```

## Current migration set (ordered)

The runner applies files lexicographically, which matches the current set:

1. `001_scan_results.sql`
2. `001b_rename_timestamp_to_scanned_at.sql`
3. `002_user_scan_history.sql`
4. `003_page_views_daily.sql`
5. `003b_increment_page_view_rpc.sql` (optional but recommended)
6. `004_statistics.sql` (only required if you rely on the statistics table)

## Fresh project verification

Quick sanity check after a new project setup:

```sql
select
  (select count(*) from public.scan_results) as scan_results_rows,
  (select count(*) from public.user_scan_history) as user_scan_history_rows,
  (select count(*) from public.page_views_daily) as page_views_daily_rows;
```

## CI migration lint

Pull requests run a lightweight lint that checks:

- Migration filename patterns
- Sorting order and duplicates
- Required migrations are present
- No usage of `CONCURRENTLY`

Run locally:

```bash
make lint-migrations
```

## Notes

- The script does **not** print secrets or connection strings
- Migrations are executed in a transaction when possible
- Autocommit is used for statements like `VACUUM`/`REINDEX`
- `CREATE INDEX CONCURRENTLY` is blocked (must be applied manually)
- Never commit real credentials to the repo

