# Supabase Postgres Verification Checklist

## Overview

If you've already:
- ✅ Set `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` in your backend deploy env
- ✅ Run the migrations (001/002/003/003b) in the Supabase SQL editor
- ✅ Your backend logs show `✓ DB backend selected: supabase`

**Then yes: you are already "on Supabase Postgres."** There's no extra "turn on Postgres" step—Supabase is Postgres.

What's "next" is just Supabase project configuration + verification so you're not guessing.

---

## ✅ Verification Steps (in order)

### 1) Run/Verify Migrations in Supabase (MUST)

In Supabase → SQL Editor, confirm tables exist:

```sql
select table_name
from information_schema.tables
where table_schema='public'
order by table_name;
```

**You should see at least:**
- `scan_results`
- `user_scan_history`
- `page_views_daily`

**Verify the function (for atomic telemetry):**

```sql
select proname
from pg_proc
where proname = 'increment_page_view';
```

**Should return:**
```
increment_page_view
```

**If missing, run migration:**
- `docs/supabase_migrations/003b_increment_page_view_rpc.sql`

---

### 2) Configure Supabase Auth (if you haven't)

**Supabase → Authentication → Providers**
- ✅ Enable Google (or other OAuth providers you need)
  - Click on "Google" provider
  - Toggle "Enable Google provider" to ON
  - **If you don't have Google OAuth credentials yet:**
    1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
    2. Create a new project (or select existing)
    3. Go to "Credentials" → "Create Credentials" → "OAuth client ID"
    4. Application type: "Web application"
    5. Authorized redirect URIs: `https://exmwrsrwhzvxcnhcflwb.supabase.co/auth/v1/callback`
    6. Copy the Client ID and Client Secret
  - Paste your Google Client ID and Client Secret into Supabase
  - Click "Save"

**Supabase → Authentication → URL Configuration**
- ✅ Add your site URLs + redirect URLs:
  - Site URL: `http://localhost:5175` (or your dev port)
  - Redirect URLs: 
    - `http://localhost:5175/**` (dev)
    - `https://your-production-domain.com/**` (prod)

**Note:** This affects login only (not DB storage).

---

### 3) Confirm Your Backend is Writing to Supabase (MUST)

**Do real actions:**
1. Sign in on the frontend
2. Run one scan
3. Visit a few pages (telemetry)

**Then check in Supabase SQL editor:**

```sql
select count(*) from public.scan_results;
select count(*) from public.user_scan_history;
select count(*) from public.page_views_daily;
```

**Counts should increase** after your actions.

---

### 4) Confirm SQLite is No Longer Used in Production (RECOMMENDED)

**Check logs again for Supabase selection:**
- Look for: `✓ DB backend selected: supabase`
- If you see `sqlite (fallback)`, check environment variables

**Optionally set explicitly in prod:**
```bash
DB_BACKEND=supabase
```

This avoids ambiguity and ensures Supabase is always used.

---

### 5) Use the DB Health Endpoint (SMART)

**Call the health endpoint to verify instantly in prod:**

```bash
curl https://your-backend.com/api/health/db
```

**Expected response:**
```json
{
  "backend": "supabase",
  "tables_ok": true,
  "can_write": true,
  "status": "healthy",
  "tables": {
    "scan_results": {"exists": true, "count": 42},
    "user_scan_history": {"exists": true, "count": 15},
    "page_views_daily": {"exists": true, "count": 128}
  },
  "functions": {
    "increment_page_view": {"exists": true}
  },
  "missing_tables": []
}
```

**What it checks:**
- ✅ Backend type (supabase/sqlite)
- ✅ Required tables exist
- ✅ `increment_page_view` function exists
- ✅ Table row counts
- ✅ Write capability

**If status is "degraded":**
- Check `missing_tables` array
- Check `error` field for details
- Verify migrations were run correctly

---

## Do You Need to "Configure Postgres from Supabase"?

**No.** Supabase already provides Postgres.

You only need to configure:

1. ✅ **Auth providers + redirect URLs** (for login)
2. ✅ **Run SQL migrations** (for tables/functions)
3. ✅ **Set environment variables** in your backend host:
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`
   - `DB_BACKEND=supabase` (optional, auto-detected)

**Optional:**
- Storage buckets (if you ever move file artifacts to Supabase Storage)

---

## Quick Verification Script

Run this in Supabase SQL Editor to verify everything at once:

```sql
-- 1. Check tables
SELECT 
  'Tables' as check_type,
  table_name as name,
  'exists' as status
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('scan_results', 'user_scan_history', 'page_views_daily')
ORDER BY table_name;

-- 2. Check function
SELECT 
  'Functions' as check_type,
  proname as name,
  'exists' as status
FROM pg_proc
WHERE proname = 'increment_page_view';

-- 3. Get row counts
SELECT 
  'scan_results' as table_name,
  COUNT(*) as row_count
FROM public.scan_results
UNION ALL
SELECT 
  'user_scan_history' as table_name,
  COUNT(*) as row_count
FROM public.user_scan_history
UNION ALL
SELECT 
  'page_views_daily' as table_name,
  COUNT(*) as row_count
FROM public.page_views_daily;
```

---

## Troubleshooting

### Backend shows "sqlite (fallback)"

**Check:**
1. `SUPABASE_URL` is set correctly
2. `SUPABASE_SERVICE_ROLE_KEY` is set correctly (not anon key!)
3. No typos in environment variable names

**Fix:**
- Set `DB_BACKEND=supabase` explicitly
- Restart backend
- Check logs for: `✓ DB backend selected: supabase`

### Tables missing

**Check:**
- Migrations were run in Supabase SQL Editor
- No errors in migration execution

**Fix:**
- Re-run migrations from `docs/supabase_migrations/`
- Check Supabase logs for errors

### Function missing

**Check:**
- Migration `003b_increment_page_view_rpc.sql` was run

**Fix:**
- Run migration in Supabase SQL Editor
- Verify with: `SELECT proname FROM pg_proc WHERE proname = 'increment_page_view';`

### Can't write to tables

**Check:**
- `SUPABASE_SERVICE_ROLE_KEY` is set (not anon key)
- Service role key has correct permissions

**Fix:**
- Use service role key (bypasses RLS)
- Verify key in Supabase → Settings → API

---

## Summary

✅ **You're on Supabase Postgres if:**
- Backend logs show: `✓ DB backend selected: supabase`
- Tables exist (verified via SQL or health endpoint)
- Backend can write (verified via health endpoint or test actions)

✅ **Next steps:**
- Verify migrations (step 1)
- Configure auth (step 2)
- Test writes (step 3)
- Use health endpoint (step 5)

No additional "Postgres configuration" needed—Supabase is Postgres! 🎉

