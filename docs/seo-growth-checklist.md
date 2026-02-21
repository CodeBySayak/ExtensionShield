# SEO Growth Checklist — Consumer Intent ("Is this Chrome extension safe?")

**Date:** 2026-02-18  
**Scope:** Routes, metadata, internal linking, sitemap, robots.

---

## PART A — Audit: What Exists vs Missing

### 1) Routes / pages

| Route | Exists? | Notes |
|-------|--------|-------|
| `/is-this-chrome-extension-safe` | **No** | Educational hub for consumer intent — **created** (see Part B). |
| `/chrome-extension-security-scanner` | **Yes** | Landing page; title/meta/canonical/OG; in sitemap. |
| `/chrome-extension-permissions` (or similar hub) | **Yes** | Evergreen permissions hub created. `/blog/how-to-check-chrome-extension-permissions` redirects to it. |
| `/research/case-studies` | **Yes** | Indexable; unique title/meta/canonical/OG; ItemList schema; in sitemap. |
| Honey as case study | **Yes** | `/research/case-studies/honey`; Article schema (dateModified/image added in implementation). |
| `/blog` | **Yes** | Blog index + post pages; posts stored in **JSON** (`src/data/blogPosts.js`), not MD/CMS. Each slug has route + sitemap entry. |

### 2) Per-page checks (existing key pages)

| Page | Title ≤60 | Meta ≤160 | Canonical | OG/Twitter + og:image | One H1 / H2 | Indexable | In sitemap | robots |
|------|-----------|-----------|-----------|------------------------|--------------|-----------|------------|--------|
| `/` | ✓ | ✓ | ✓ | ✓ (seoUtils) | ✓ | ✓ | ✓ | Allowed |
| `/scan` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Allowed |
| `/chrome-extension-security-scanner` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Allowed |
| `/research/case-studies` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Allowed |
| `/research/case-studies/honey` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Allowed |
| `/research/methodology` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Allowed |
| `/blog` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Allowed |

`og:image` is absolute via `getOGImage()` → `https://extensionshield.com/og.png`.

### 3) Internal linking (before fixes)

| Required link | Status before |
|---------------|----------------|
| Home → /scan | ✓ (hero CTA + scan input) |
| Home → educational hub | **Missing** → added: "Learn how to check if an extension is safe" → `/is-this-chrome-extension-safe` |
| Hub → /scan | N/A (hub created with CTA to /scan) |
| Hub → methodology + case studies | N/A (hub created with links) |
| Case studies → /scan + hub | Honey had /scan CTA only; **hub link added** to Honey + PDF + Fake ad blockers |
| Footer: Scan, Methodology, Case Studies, Compare, Enterprise, Blog | **Missing:** Scan, Case Studies, hub link → **added** |

---

## PART B — What Was Created

### 4) Educational hub: `/is-this-chrome-extension-safe`

- **Route:** `/is-this-chrome-extension-safe`
- **Component:** `frontend/src/pages/landing/IsThisChromeExtensionSafePage.jsx`
- **Content:** H1 "Is this Chrome extension safe?"; short intro (what “safe” means: permissions, network, updates); 3-step checklist; "Try it now" CTA (link to /scan); "What ExtensionShield checks" (permissions, domains, CSP, etc.); FAQ (6–8 Qs).
- **SEO:** Unique title (≤60) and meta description (≤160); canonical; OG/Twitter via SEOHead; FAQPage JSON-LD matching visible FAQs; BreadcrumbList (Home > Guide); indexable; added to routes and sitemap.

### 5) Case studies

- **Existing:** `/research/case-studies` (index), Honey, PDF converters, Fake ad blockers — all indexable, with structure (What happened / findings / takeaways). Honey already had CTA to /scan.
- **Strengthened:**  
  - Added link to hub ("Learn how to check if an extension is safe") in Honey, PDF converters, and Fake ad blockers CTA blocks.  
  - Article JSON-LD on case study pages: added `dateModified` and optional `image` where applicable (Honey; PDF/Fake ad blockers use same pattern).

No new case-study stub pages were added: three full case studies (Honey, PDF converters, Fake ad blockers) already exist beyond the listing page.

---

## PART C — Linking Policy (Implemented)

- **Home:** Link "Learn how to check if an extension is safe" → `/is-this-chrome-extension-safe` (in hero area or near FAQ).
- **Footer:** Added **Scan** → `/scan`, **Case Studies** → `/research/case-studies`, **Is extension safe?** (hub) → `/is-this-chrome-extension-safe`. Retained: How We Score, Compare, Enterprise, Blog, Privacy, Contribute, GitHub.
- **Scanner (/scan):** In "Related" block: added "How to interpret results" → `/is-this-chrome-extension-safe`.
- All new/updated pages that should rank are linked from at least one of: Home, footer, or hub. Nothing rankable was left unlinked.

---

## PART D — Sitemap & robots

- **Sitemap:** New route `/is-this-chrome-extension-safe` has `seo` in `routes.jsx`; `npm run generate:sitemap` (run by `npm run build`) includes it. Sitemap referenced in robots.txt.
- **robots.txt:** `User-agent: *` Allow: /; Sitemap: https://extensionshield.com/sitemap.xml; Disallow only /settings, /reports; AI crawlers disallowed separately. Hub and case-study routes are **not** blocked.

---

## Internal linking map (bullet list)

- **Home** → /scan (hero), /is-this-chrome-extension-safe ("Learn how to check…"), /research/case-studies (e.g. Honey section), /research/methodology, /enterprise (sections), /compare (footer).
- **Hub (/is-this-chrome-extension-safe)** → /scan (primary CTA), /chrome-extension-permissions, /research/methodology, /research/case-studies (index + Real examples cards: Honey, PDF converters, Fake ad blockers), /compare, /crxcavator-alternative, /enterprise (in "Related").
- **Permissions hub (/chrome-extension-permissions)** → /scan (CTA), /is-this-chrome-extension-safe, /research/methodology, /glossary.
- **Scanner (/scan)** → /is-this-chrome-extension-safe ("How to interpret results"), /research/methodology, /enterprise, /compare, /crxcavator-alternative.
- **Case studies index** → each case study URL; each case study page → /scan, /is-this-chrome-extension-safe, /research/case-studies.
- **Footer** → Scan, How We Score (methodology), Case Studies, Compare, Enterprise, Blog, Is extension safe? (hub), Privacy, Contribute, GitHub.

---

### Hub cluster (later updates)

- **Hub title:** "Is This Chrome Extension Safe? | ExtensionShield" (≤60 chars). Route + SEOHead updated.
- **Hub TOC:** Under intro; anchors #checklist, #what-we-check, #examples, #faq, #scan; sections have matching ids.
- **Real examples:** 3 cards on hub → /research/case-studies/honey, /research/case-studies/pdf-converters, /research/case-studies/fake-ad-blockers.
- **Permissions hub:** /chrome-extension-permissions — evergreen permissions explained; CTA to /scan, link to /is-this-chrome-extension-safe. Blog post /blog/how-to-check-chrome-extension-permissions redirects to it.
- **Comparing scanners:** Hub and /scan include link to /crxcavator-alternative.

---

*After adding or changing routes, run `npm run generate:sitemap` or `npm run build` to refresh sitemap.xml.*
