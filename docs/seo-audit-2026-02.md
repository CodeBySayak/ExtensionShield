# ExtensionShield SEO Audit

**Audit date:** 2026-02-18  
**Scope:** All public routes, sitewide technical SEO, Core Web Vitals pass.

---

## 1. SEO Status Report

### What’s good
- **Reusable SEO layer:** `SEOHead` component with react-helmet-async; sets title, meta description, canonical, Open Graph, Twitter Card, optional noindex, and JSON-LD.
- **Canonical & domain:** `seoUtils.js` uses a single canonical domain (extensionshield.com); canonical URLs are correct.
- **Sitemap:** `scripts/generate-sitemap.js` builds sitemap from route config; run via `npm run generate:sitemap` and wired into `npm run build`. Valid XML, includes all static SEO routes.
- **robots.txt:** Present in `public/robots.txt`; allows `User-agent: *`, `Allow: /`, references sitemap; disallows `/settings` and `/reports`.
- **Route-level SEO:** Most public routes have `seo: { title, description, canonical }` in `routes.jsx`; many pages use `SEOHead` with that data.
- **Structured data:** Home has Organization + SoftwareApplication + FAQPage JSON-LD; Enterprise has FAQPage. Scanner page does not yet have SoftwareApplication on the page.
- **Dynamic / scan results:** `/scan/results/:scanId` correctly uses `noindex` (transient content).
- **Heading structure:** Key pages (Home, Methodology, Compare, Enterprise) have a single H1 and logical H2→H3 hierarchy.
- **Indexability:** No accidental noindex on main marketing pages; auth/diagnostics uses noindex by design.

### What’s broken / at risk
- **Homepage title length:** With `getPageTitle()` the full title becomes “Chrome Extension Security Scanner | Browser Extension Security Scanner | ExtensionShield” (~78 chars). SERP titles are typically truncated at ~60 characters; primary keyword may be cut off.
- **Default title in `index.html`:** Long default title/description; crawlers that run before React may see this if JS is slow or blocked (SPA caveat).
- **AI crawlers:** robots.txt does not disallow AI training bots (e.g. GPTBot, Claude-Web, etc.). Request was to allow Googlebot/Bingbot but block AI training bots.
- **Blog 404:** When `BlogPostPage` has no matching post it renders “Post not found” without setting `noindex` or a proper 404 status/canonical.
- **Missing keyword landing pages:** No dedicated routes for high-intent slugs: `/chrome-extension-security-scanner`, `/browser-extension-risk-assessment`, `/crxcavator-alternative`. These are required for the backlog.

### What’s missing
- **Internal linking:** Footer does not link to Compare, Enterprise, or Methodology. No “Related reads” / “See also” blocks linking scanner → methodology → enterprise → API/compare.
- **Pricing page:** No `/pricing` route; not in scope as a “fix” but noted for product roadmap.
- **Scanner page JSON-LD:** Scanner page does not output SoftwareApplication/WebApplication schema (home does; scanner is the main product entry point).
- **Methodology FAQ schema:** Methodology page could carry a small FAQPage JSON-LD for “How we score” FAQs.
- **Sitemap reference in robots:** Sitemap URL is present; ensure it stays in sync when new routes (e.g. new landing pages) are added.
- **Performance / CWV:** Google Fonts loaded with `display=swap`; no preload for critical font. Hero images and render-blocking not audited in depth here; recommend a separate CWV pass (LCP/CLS/INP).
- **SSR/prerender:** SPA only; first paint is app shell. Marketing pages (home, scanner, methodology, enterprise, compare, new landing pages) would benefit from prerender or SSG for crawlers if needed later.

---

## 2. Findings per page (summary table)

| Route | Unique title | Title ≤60 | Meta desc | Desc ≤160 | Canonical | OG + Twitter | One H1 | Hierarchy | Indexable | Notes |
|-------|--------------|-----------|-----------|-----------|-----------|--------------|--------|-----------|-----------|--------|
| `/` | ✓ | ❌ (78) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Shorten title |
| `/scan` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Add SoftwareApplication |
| `/scan/history` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| `/scan/results/:id` | — | — | ✓ | — | ✓ | ✓ | — | — | noindex ✓ | By design |
| `/research` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| `/research/methodology` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Add FAQ schema |
| `/research/case-studies` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| `/research/benchmarks` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| `/compare` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| `/compare/crxcavator` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| `/compare/crxplorer` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| `/compare/extension-auditor` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| `/blog` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| `/blog/:slug` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 404: no noindex |
| `/enterprise` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| `/about`, `/open-source`, `/community`, etc. | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| `/chrome-extension-security-scanner` | — | — | — | — | — | — | — | — | — | **Missing** |
| `/browser-extension-risk-assessment` | — | — | — | — | — | — | — | — | — | **Missing** |
| `/crxcavator-alternative` | — | — | — | — | — | — | — | — | — | **Missing** |

---

## 3. Prioritized fix list

### P0 (Critical – do first)
- Shorten homepage `<title>` so full string is ≤60 characters (e.g. “Chrome Extension Security Scanner | ExtensionShield”) and align with meta description.
- Add three keyword landing pages with unique title/description/canonical/OG/Twitter and one H1 each:
  1. `/chrome-extension-security-scanner` (consumer intent)
  2. `/browser-extension-risk-assessment` (enterprise intent)
  3. `/crxcavator-alternative` (comparison intent)
- Ensure `robots.txt` allows Googlebot/Bingbot and disallows common AI training crawlers (e.g. GPTBot, Claude-Web) without blocking search engines.

### P1 (High)
- Add SoftwareApplication (or WebApplication) JSON-LD on the scanner page (`/scan`).
- Add FAQPage JSON-LD on methodology page for “How we score” FAQs.
- Update footer nav: add Compare, Enterprise, Methodology (and optionally API/docs if present).
- Add “Related reads” / “See also” blocks: Scanner → Methodology → Enterprise → Compare (and to new landing pages where relevant).
- Ensure sitemap generator includes the three new landing page routes (and any future static SEO routes).
- Optional: add `og:image` default in `SEOHead`/seoUtils if not already set (already present; verify absolute URL).

### P2 (Nice to have)
- Blog 404: set noindex and/or 404 semantics when post not found.
- Preload critical font(s) for LCP; audit hero images and layout shifts (CLS/INP).
- Consider prerender/SSG for key marketing routes for crawlers.
- Add a dedicated “API” or “Docs” link in footer when those routes exist.

---

## 4. Implementation checklist (P0 + P1)

- [x] Shorten home title and align index.html default.
- [x] Create `/chrome-extension-security-scanner` page + route + sitemap.
- [x] Create `/browser-extension-risk-assessment` page + route + sitemap.
- [x] Create `/crxcavator-alternative` page + route + sitemap.
- [x] Update robots.txt: allow Googlebot/Bingbot; disallow AI training bots.
- [x] Scanner page: SoftwareApplication JSON-LD (already present; verified).
- [x] Methodology page: add FAQPage JSON-LD and align title with route.
- [x] Footer: add Compare, Enterprise, Methodology (internal linking).
- [x] Related reads blocks: scanner, methodology, enterprise, compare/landing pages.
- [x] Sitemap: new routes included via existing generator (32 routes after run).

---

*Generated as part of technical SEO audit. Re-run sitemap after route changes: `npm run generate:sitemap` (or rely on `npm run build`).*
