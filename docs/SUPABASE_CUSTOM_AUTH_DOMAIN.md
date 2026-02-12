# Supabase Custom Auth Domain Setup

This document describes how ExtensionShield configured a **custom auth domain** (`login.extensionshield.com`) for Supabase so that Google sign-in shows a branded domain instead of the default Supabase project URL. It is written for anyone who needs to repeat or understand the process.

---

## Table of Contents

1. [Goal and Why It Matters](#goal-and-why-it-matters)
2. [Concepts You Need](#concepts-you-need)
3. [Prerequisites (Preflight)](#prerequisites-preflight)
4. [Phase 1: DNS CNAME Record in Cloudflare](#phase-1-dns-cname-record-in-cloudflare)
5. [Phase 2: Register Custom Domain in Supabase](#phase-2-register-custom-domain-in-supabase)
6. [Phase 3: TXT Verification in Cloudflare](#phase-3-txt-verification-in-cloudflare)
7. [Phase 4: Verify and Activate in Supabase](#phase-4-verify-and-activate-in-supabase)
8. [Phase 5: Google OAuth Redirect URI](#phase-5-google-oauth-redirect-uri)
9. [Phase 6: Supabase Auth URL Configuration](#phase-6-supabase-auth-url-configuration)
10. [Phase 7: App and Redeploy](#phase-7-app-and-redeploy)
11. [Troubleshooting](#troubleshooting)
12. [Checklist Summary](#checklist-summary)

---

## Goal and Why It Matters

**Goal:** When users click “Sign in with Google,” the Google consent screen should say **“Continue to login.extensionshield.com”** (or your chosen subdomain), not **“Continue to exmwrsrwhzvxcnhcflwb.supabase.co.”**

**Why it matters:**

- **Trust:** A random project ID in the URL looks technical and can reduce confidence.
- **Branding:** Your product name in the URL reinforces that the sign-in is part of your app.
- **Consistency:** Your main site is `extensionshield.com`; having auth on a clear subdomain (e.g. `login.extensionshield.com`) keeps the experience coherent.

Supabase supports **custom domains** for the Auth host. You point a subdomain (e.g. `login.extensionshield.com`) at Supabase via DNS, prove you control the domain with a TXT record, and then Supabase issues SSL and serves Auth from that hostname. Your app and Google OAuth are then configured to use that URL.

---

## Concepts You Need

### CNAME record

A **CNAME** (Canonical Name) record says: “This hostname is another name for another hostname.”  
Example: `login.extensionshield.com` → `exmwrsrwhzvxcnhcflwb.supabase.co`.

- Browsers and APIs resolve `login.extensionshield.com` and end up at Supabase’s servers.
- Supabase needs to **see this CNAME** when it checks your domain (for custom domain and SSL). If the CNAME is hidden (e.g. by a proxy), verification fails.

### DNS-only vs Proxied (Cloudflare)

In Cloudflare, each record has a **proxy status**:

- **Proxied (orange cloud):** Traffic goes through Cloudflare. Cloudflare answers DNS with **its own IP addresses**. The CNAME is resolved by Cloudflare; the rest of the internet does **not** see the CNAME, only Cloudflare’s A records.
- **DNS only (grey cloud):** Cloudflare only answers DNS; it returns the **real** CNAME (or the result of resolving it). Traffic to your service goes directly to the target (e.g. Supabase), not through Cloudflare.

**Why the auth subdomain must be DNS-only:**  
Supabase (and its SSL provider) performs a **CNAME lookup** to verify that `login.extensionshield.com` points to their host. If the record is proxied, that lookup does not return the CNAME; it returns Cloudflare’s IPs. Supabase then reports “Your CNAME record cannot be found.” So for the **auth** subdomain we use **DNS only**. Your main site (`extensionshield.com`) can stay **Proxied** to keep Cloudflare’s protection and CDN.

### TXT record and domain verification

To prove you control the domain, Supabase asks you to add a **TXT** record with a secret value they give you. Their servers look up that TXT record; if the value matches, they consider the domain yours. This is standard for domain ownership and for ACME (SSL certificate) challenges. The name is usually something like `_acme-challenge.login.extensionshield.com` and the content is a one-time token.

### Redirect URI (Google OAuth)

When you use “Sign in with Google,” the flow is: your app sends the user to Google, and Google sends them back to a **redirect URI** (e.g. `https://login.extensionshield.com/auth/v1/callback`). Google only allows redirects to URIs that you have listed in the OAuth client’s **Authorized redirect URIs**. If the URI in the request does not **exactly** match one of those entries (including scheme, host, and path), Google returns **Error 400: redirect_uri_mismatch**. So after switching to a custom auth domain, you must add the new callback URL in Google Cloud Console.

---

## Prerequisites (Preflight)

Before changing anything, confirm:

1. **Cloudflare is authoritative** for `extensionshield.com` (your domain’s nameservers point to Cloudflare).
2. **Supabase Custom Domains** are available for your project (paid plan or add-on). Custom domains are not included in the Supabase Free plan.
3. You have access to **Google Cloud Console** for the OAuth client used by Supabase (Google provider).
4. You can use either the **Supabase Dashboard** or the **Supabase CLI** for adding and verifying the custom domain.

---

## Phase 1: DNS CNAME Record in Cloudflare

**What you do:** Create a CNAME that points your chosen auth subdomain to your Supabase project host.

**Steps:**

1. In Cloudflare: **Websites** → **extensionshield.com** → **DNS** → **Records** → **Add record**.
2. Set:
   - **Type:** CNAME  
   - **Name:** `login` (for `login.extensionshield.com`; Cloudflare appends the zone name).  
   - **Target:** `exmwrsrwhzvxcnhcflwb.supabase.co` (your project ref from Supabase).  
   - **Proxy status:** **DNS only (grey cloud).**  
   - **TTL:** Auto or 1 min for faster propagation.
3. Save.

**Verification:** After a few minutes, run:

- `dig login.extensionshield.com CNAME +short`

You should see the target hostname (e.g. `exmwrsrwhzvxcnhcflwb.supabase.co.`). If you see Cloudflare IPs instead and no CNAME, the record is still Proxied — switch it to DNS only.

---

## Phase 2: Register Custom Domain in Supabase

**What you do:** Tell Supabase you want to use `login.extensionshield.com` as the Auth host.

**Steps:**

1. Supabase Dashboard → your **Project** → **Settings** → **Custom Domains**.
2. Click **Add custom domain** (or equivalent).
3. Enter: `login.extensionshield.com`.
4. Supabase will first check for the **CNAME** (Phase 1). If it finds it, you may be taken to **TXT verification** (Phase 3). If not, it will ask you to add the CNAME and show “Your CNAME record cannot be found” until the record is DNS-only and propagated.

**Concept:** Supabase needs the CNAME to be visible so it can bind SSL and route Auth traffic to your subdomain.

---

## Phase 3: TXT Verification in Cloudflare

**What you do:** Add the TXT record Supabase gives you so it can confirm you control the domain (and complete SSL issuance).

**Steps:**

1. On the Supabase Custom Domains page, copy the **TXT record** it shows:
   - **Name:** e.g. `_acme-challenge.login.extensionshield.com` (in Cloudflare you often enter only the subdomain part: `_acme-challenge.login`).
   - **Content:** the token string (e.g. `ynmDt1QLKDCDY0wV03q0TSq` or a longer value — use exactly what Supabase shows).
2. In Cloudflare: **DNS** → **Add record**:
   - **Type:** TXT  
   - **Name:** `_acme-challenge.login`  
   - **Content:** paste the exact value from Supabase.  
   - **TTL:** Auto or 1 min.
3. Save.
4. Wait 1–2 minutes for propagation.

**Verification:** Run:

- `dig TXT _acme-challenge.login.extensionshield.com +short`

The output should contain the exact token Supabase showed. If the value differs (e.g. old token, typo), update the TXT in Cloudflare to match Supabase and wait before clicking Verify again.

---

## Phase 4: Verify and Activate in Supabase

**What you do:** Let Supabase verify the TXT (and CNAME), then activate the custom domain.

**Steps:**

1. Back in Supabase Custom Domains, click **Verify**. Supabase will check the TXT (and CNAME). If “Unable to verify” appears, wait a bit and try again; DNS can take a minute or two.
2. Once verification succeeds, click **Activate** (or equivalent) so the domain becomes the active Auth host.
3. Confirm the UI shows something like: **“Active custom domain: login.extensionshield.com — Your custom domain is currently active and is serving traffic.”**

After this, Auth is served from `https://login.extensionshield.com`. SSL is handled by Supabase.

---

## Phase 5: Google OAuth Redirect URI

**What you do:** Add the new callback URL to your Google OAuth client so Google allows redirects to your custom auth domain.

**Steps:**

1. **Google Cloud Console** → **APIs & Services** → **Credentials**.
2. Open the **OAuth 2.0 Client ID** that Supabase uses for Google sign-in (the one whose Client ID is in Supabase → Authentication → Providers → Google).
3. Under **Authorized redirect URIs**, add:
   - `https://login.extensionshield.com/auth/v1/callback`
   (Use your exact custom domain and path; no trailing slash.)
4. You can keep the existing Supabase default URL (`https://exmwrsrwhzvxcnhcflwb.supabase.co/auth/v1/callback`) until you have fully switched the app to the custom domain.
5. Save.

**Concept:** The redirect URI in each sign-in request must exactly match one of these entries. If your app (via Supabase) sends `https://login.extensionshield.com/auth/v1/callback` but that URI is not in the list, Google returns **redirect_uri_mismatch**.

---

## Phase 6: Supabase Auth URL Configuration

**What you do:** Set where users should land after sign-in and which redirect URLs are allowed.

**Steps:**

1. Supabase Dashboard → **Authentication** → **URL Configuration**.
2. **Site URL:** Your main app URL, e.g. `https://extensionshield.com`.
3. **Redirect URLs:** Add the URLs your app uses after auth, for example:
   - `https://extensionshield.com/**`
   - `http://localhost:5173/**`
   - Any specific callback path you use (e.g. `https://extensionshield.com/auth/callback`).

This does not change the Auth host itself (that’s the custom domain); it defines where Supabase redirects users after successful sign-in and which origins are allowed.

---

## Phase 7: App and Redeploy

**What you do:** Point the app’s Supabase client at the custom auth URL and redeploy so the frontend uses it.

**Concept:** The frontend is built with a **Supabase URL** (e.g. from `VITE_SUPABASE_URL`). That URL is the Auth host. If it stays as `https://exmwrsrwhzvxcnhcflwb.supabase.co`, the browser will still open the default Supabase domain for sign-in and cookies will be set for that host. To get the branded experience and correct cookies, the app must use the custom URL (e.g. `https://login.extensionshield.com`) as the Supabase URL.

**Steps:**

1. In your app’s config (e.g. environment variables used at build time), set the Supabase URL to `https://login.extensionshield.com` (no path).
2. Rebuild the frontend and redeploy (e.g. push to trigger Railway or run your deploy process).
3. After deploy, test sign-in in an incognito window; the Google screen should show “Continue to login.extensionshield.com.”

**Note:** If you only add the custom domain and update Google redirect URIs but do **not** change the app’s Supabase URL and redeploy, the app will keep using the default Supabase host and the consent screen will not show your branded domain.

---

## Troubleshooting

### “Your CNAME record for login.extensionshield.com cannot be found”

- Ensure the CNAME exists and the **Name** is correct (e.g. `login` for `login.extensionshield.com`).
- **Set the record to DNS only (grey cloud)** in Cloudflare. Proxied records hide the CNAME.
- Wait a few minutes and run `dig login.extensionshield.com CNAME +short`; you should see the Supabase target.

### “Unable to verify records from DNS provider yet” (TXT)

- Confirm the TXT **Name** in Cloudflare matches what Supabase expects (e.g. `_acme-challenge.login` so the full name is `_acme-challenge.login.extensionshield.com`).
- Confirm the TXT **Content** is exactly what Supabase shows (copy again from the Verify page).
- Wait 1–2 minutes and run `dig TXT _acme-challenge.login.extensionshield.com +short`; the value should match.
- Click **Verify** again in Supabase.

### Error 400: redirect_uri_mismatch (Google)

- The redirect URI sent in the request must **exactly** match an **Authorized redirect URI** in the OAuth client (same scheme, host, path; no trailing slash).
- Add `https://login.extensionshield.com/auth/v1/callback` (or your custom auth URL + `/auth/v1/callback`) in Google Cloud Console and save.
- Ensure the app is using the custom Supabase URL so the redirect URI is the custom domain, not the default Supabase host.

### Google still shows the old Supabase domain

- Confirm in Supabase that the custom domain is **Active**.
- Confirm the app’s Supabase URL env (e.g. `VITE_SUPABASE_URL`) is set to `https://login.extensionshield.com` and that the app was **rebuilt and redeployed** after the change.
- Try an incognito window or another browser to avoid cached consent screens.

---

## Checklist Summary

| Step | Where | Action |
|------|--------|--------|
| 1 | Cloudflare | CNAME `login` → `exmwrsrwhzvxcnhcflwb.supabase.co`, **DNS only** |
| 2 | Supabase | Add custom domain `login.extensionshield.com` |
| 3 | Cloudflare | TXT `_acme-challenge.login` with token from Supabase |
| 4 | Supabase | Click Verify, then Activate; confirm “Active custom domain” |
| 5 | Google Cloud | Add redirect URI `https://login.extensionshield.com/auth/v1/callback` |
| 6 | Supabase | Set Site URL and Redirect URLs in Auth → URL Configuration |
| 7 | App + Railway | Set Supabase URL to `https://login.extensionshield.com`, rebuild, redeploy |

**Reference for this project:**

- Supabase project ref: `exmwrsrwhzvxcnhcflwb`
- Custom auth domain: `login.extensionshield.com`
- Main site: `https://extensionshield.com`
- Local dev: `http://localhost:5173`

---

*Document created from the setup performed for ExtensionShield. Update the project ref and domain names if reusing for another project or domain.*
