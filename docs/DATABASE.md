# Database & Supabase Postgres

This doc explains how scan storage and manifest lookup work, and how to link and use Supabase Postgres for the API and for direct DB assessment.

---

## 0. Local dev: see the same data as production

To have your **local** app use the **same** Supabase database as production (no SQLite):

1. **Backend** (project root `.env`): set `DB_BACKEND=supabase`, `SUPABASE_URL`, and `SUPABASE_SERVICE_ROLE_KEY` (from Supabase Dashboard → API).
2. **Frontend** (`frontend/.env`): set `VITE_API_URL=http://localhost:8007` so the UI talks to your local API.
3. Run the API locally; the frontend will show the same scan results as production.

If `DB_BACKEND` is not set or Supabase keys are missing, the backend falls back to **SQLite** (local file only; different data from prod). Prefer Supabase for local so you see production data.

---

## 1. Extension storage and manifest lookup (ZIP upload)

**Where things live**

- **Uploaded file**: Saved under `EXTENSION_STORAGE_PATH` (e.g. `/app/extensions_storage` in prod, or `extensions_storage` in dev). The API uses `RESULTS_DIR`, which is the same as `extension_storage_path` (resolved).
- **Extraction**: ZIP/CRX is extracted to `EXTENSION_STORAGE_PATH/extracted_<basename>_<pid>` (e.g. `extracted_cf56dcb8-..._aapbdbdomjkkjkaonfhkkikfgjllcleb.zip_10`).
- **Manifest search**: The code **always searches under that extracted directory** (i.e. under extension storage). It looks for `manifest.json` (case-insensitive) at the root of the extract or in subdirectories. If the ZIP has a single top-level folder (e.g. `MyExtension/manifest.json`), the resolver picks that folder as the extension root.

**If you see "manifest.json not found in /app/extensions_storage/extracted_..."**

- The path is correct: we are searching under extension storage.
- The error means no `manifest.json` was found at the top level of the extract **and** either:
  - There is no `manifest.json` anywhere in the ZIP (invalid or wrong file), or
  - There are multiple directories containing `manifest.json` and the resolver could not pick one (we now pick the shallowest).
- Check the logs: we log **top-level contents** of the extract dir when no manifest is found, so you can see what was actually extracted.
- Ensure the ZIP is a valid Chrome extension: `manifest.json` at the root of the ZIP or inside **one** top-level folder.

**Dev vs backend**

- Set `EXTENSION_STORAGE_PATH` in `.env` (e.g. `extensions_storage` for dev, `/app/extensions_storage` in Docker/Railway). Same behavior on dev and backend as long as this is set.

---

## 2. Linking Supabase Postgres

The app uses **Supabase** for Postgres in production. Scan results are stored in a table (default: `scan_results`). You can use the same Postgres for the API and for direct queries.

### 2.1 Env vars for the API (scan save/load)

These are used by the backend to talk to Supabase (REST/PostgREST), not a raw Postgres connection:

```bash
DB_BACKEND=supabase
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<your-service-role-key>
# Optional
SUPABASE_SCAN_RESULTS_TABLE=scan_results
```

- Get **SUPABASE_URL** and **SUPABASE_SERVICE_ROLE_KEY** from the Supabase dashboard: Project Settings → API. Use the **service_role** key only on the server (never in the frontend).
- With these set, the API reads/writes scan results via the Supabase client (no direct Postgres URL needed for normal runs).

### 2.2 Direct Postgres connection (migrations, scripts, DB assessment)

For running migrations, ad-hoc SQL, or tools that need a direct Postgres connection, use one of:

**Option A – Connection string (recommended)**

Supabase dashboard: Project Settings → Database → Connection string (URI). Use the **URI** format and set:

```bash
# Direct Postgres (for migrations, psql, and your own DB scripts)
DATABASE_URL=postgresql://postgres.[project-ref]:[YOUR-PASSWORD]@aws-0-[region].pooler.supabase.com:6543/postgres
# Or the direct (non-pooler) URL on port 5432 if you need it
# SUPABASE_DB_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[project-ref].supabase.co:5432/postgres
```

- Replace `[YOUR-PASSWORD]` with the database password from Project Settings → Database.
- Use **Transaction** mode (port 6543) for migrations; use **Session** (port 5432) if a script needs sessions.

**Option B – Individual Postgres env vars**

```bash
PGHOST=aws-0-<region>.pooler.supabase.com
PGPORT=6543
PGDATABASE=postgres
PGUSER=postgres.<project-ref>
PGPASSWORD=<your-database-password>
```

### 2.3 Linking the project (Supabase CLI, optional)

If you use the Supabase CLI for migrations and linking:

```bash
# Install Supabase CLI if needed
# npm install -g supabase   or   brew install supabase/tap/supabase

# Log in and link to your project (use project ref from dashboard URL)
supabase login
supabase link --project-ref <project-ref>

# Push migrations
supabase db push
```

Without the CLI, use the migrations script with `DATABASE_URL` or `PG*` set (see below).

---

## 3. Running migrations and making DB calls

### 3.1 Apply migrations (with direct Postgres)

Ensure `DATABASE_URL` or `SUPABASE_DB_URL` (or `PGHOST`/`PGPORT`/`PGDATABASE`/`PGUSER`/`PGPASSWORD`) is set, then:

```bash
# From repo root; uses supabase/migrations/
python scripts/run_supabase_migrations.py
```

Or with `make` (if defined):

```bash
make run-migrations
```

### 3.2 Validate API + Postgres

```bash
# Requires DB_BACKEND=supabase and SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY
make validate-postgres
# Or:
VALIDATE_EXTENSION_ID=<extension_id> python scripts/validate_postgres_local.py
```

### 3.3 Making your own DB calls

- **From the backend (Python)**: Use the existing `db` object (Supabase client). For raw SQL you’d add a small script or endpoint that uses `psycopg`/`psycopg2` with `DATABASE_URL` or `PG*` from env.
- **From the frontend**: Never use the service role key or direct Postgres. Use the Supabase client with the **anon** key and RLS, or call your backend API.
- **CLI / one-off scripts**: Use `DATABASE_URL` (or `PG*`) and connect with `psql` or a script:

  ```bash
  psql "$DATABASE_URL" -c "SELECT extension_id, scanned_at FROM scan_results LIMIT 5;"
  ```

---

## 4. Summary

| Goal                         | What to set                                                                 | Where to get it |
|-----------------------------|-----------------------------------------------------------------------------|-----------------|
| API uses Supabase for scans | `DB_BACKEND=supabase`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`          | Dashboard → API |
| Run migrations              | `DATABASE_URL` or `SUPABASE_DB_URL` or `PGHOST`/`PGPORT`/…                  | Dashboard → Database |
| Direct queries / psql       | Same as migrations                                                          | Dashboard → Database |
| Extension storage (ZIP)     | `EXTENSION_STORAGE_PATH` (same on dev and backend)                          | Your choice (e.g. `extensions_storage`, `/app/extensions_storage`) |

All manifest lookup for uploaded ZIPs is done under **extension storage** (`EXTENSION_STORAGE_PATH`); the "manifest.json not found in /app/extensions_storage/..." message confirms we are searching there and that the ZIP layout or contents need to be fixed.
