# Google Tag (gtag) – How to see it in Network tab

## Why you might not see it

1. **Ad blocker or privacy extensions**  
   uBlock Origin, Privacy Badger, Brave shields, etc. often **block** `googletagmanager.com` and `google-analytics.com`. Those requests never appear in the Network tab.  
   **Try:** Incognito/Private window with extensions disabled, or another browser without ad blockers.

2. **Network filter**  
   The first request is the **script** load:  
   `https://www.googletagmanager.com/gtag/js?id=AW-17954318055`  
   That is a **JS** request, not Fetch/XHR.  
   **Try:** In Network tab choose **“All”** (or **“JS”**), or type `googletagmanager` or `gtag` in the filter box.

3. **Deployment / cache**  
   If the live site (e.g. extensionshield.com) is serving an old build or cached HTML, the tag might not be in the page.  
   **Try:** Hard reload (Ctrl+Shift+R / Cmd+Shift+R), or redeploy the latest frontend build.

4. **Cloudflare HTML minify**  
   If Cloudflare “Auto Minify” is enabled for **HTML**, it can change the inline gtag script (e.g. remove newlines). Then the CSP hash no longer matches and the browser can block the inline script.  
   **Try:** In Cloudflare Dashboard → Speed → Optimization → disable **HTML** minify for this zone, or leave HTML minify off.

## Quick checks in the browser

- **Console:** Reload the page, then run:
  - `window.gtag` → should be a function.
  - `window.dataLayer` → should be an array with at least one item.
- **Network:** Reload with “Preserve log” off, filter **All**, then look for:
  - `gtag/js?id=AW-17954318055` (type: script)
  - Or filter by: `googletagmanager`

## Where the tag is in the repo

- **HTML:** `frontend/index.html` – comment, async script, and inline `dataLayer` + `gtag('config', …)`.
- **CSP:** Allowing the inline script by hash in `frontend/vite.config.js` and `frontend/public/_headers` (so no `unsafe-inline`).
