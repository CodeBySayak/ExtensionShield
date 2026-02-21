# CMS & Editorial Workflow Implementation Plan — ExtensionShield

**Purpose:** Move content (blog, and optionally case studies / landing copy) into a CMS with a real editorial workflow: roles, drafts, review, scheduled publishing, revisions, media, taxonomy, and SEO fields.

**Status:** Plan (feasibility confirmed against current codebase).  
**Last updated:** 2026-02-20.

---

## 1. Feasibility Summary

**Conclusion: Yes, it is possible.**

- **Current state (verified):**
  - **Blog:** Stored in `frontend/src/data/blogPosts.js` (JSON). Each post has `slug`, `title`, `description`, `date`, `category`, `sections[]` (heading + body). No CMS, no workflow.
  - **Routes:** Blog routes are static in `frontend/src/routes/routes.jsx` (e.g. `/blog/:slug` → `BlogPostPage`). `BlogPostPage` resolves content via `getBlogPostBySlug(slug)` from the JSON file.
  - **SEO:** `SEOHead` already supports title, description, pathname (→ canonical), OG, Twitter, optional `ogImage`/`schema`. `seoUtils.js` provides `getCanonicalUrl`, `getOGImage`, `getPageTitle`, OG/Twitter tag helpers.
  - **Sitemap:** Generated at build time from `routes.jsx` by `frontend/scripts/generate-sitemap.js`; only static paths with `seo` are included. Blog slugs are today explicit routes, so new posts require route + sitemap changes unless we make blog routes/sitemap dynamic.
  - **Backend:** FastAPI; no content API today. Optional Supabase for auth/data.
- **What we need:** A CMS with the workflow below, a way for the frontend to get published content (API or build-time fetch), and a strategy for dynamic blog routes and sitemap so new posts don’t require code changes.

---

## 2. Target Workflow (Requirements)

| Requirement | Description |
|-------------|-------------|
| **Roles** | Writer / Editor / Publisher (or equivalent: create+draft, review+edit, publish) |
| **Drafts + review** | Content can be draft → in review → approved; only published visible on site |
| **Scheduled publishing** | Publish date/time; content goes live automatically when scheduled |
| **Revisions + rollback** | Full revision history per item; ability to roll back to a previous revision |
| **Media library** | Upload, organize, and attach images (and optionally other assets) to content |
| **Taxonomy / tags** | Categories and/or tags for filtering, related content, and SEO |
| **SEO fields** | Per-item: meta title, meta description, canonical URL, Open Graph (and optionally OG image override); used by existing `SEOHead` |

---

## 3. CMS Options Comparison

| Criteria | Drupal | Directus | Strapi |
|----------|--------|----------|--------|
| **Workflow maturity** | Strong (Workflows, Content Moderation, revisions, scheduling in core/contrib) | Good (flows, roles; scheduling may need extension/custom) | Good (draft/publish, RBAC; scheduling via plugin or custom) |
| **Roles (Writer/Editor/Publisher)** | Native (roles + workflows) | Roles + flows | Roles + lifecycle |
| **Revisions + rollback** | Core revisioning + revert | Possible (versioning / snapshots depending on version) | Via versioning plugin or custom |
| **Scheduled publishing** | Scheduler module / core | Custom or extension | Scheduler plugin or cron job |
| **Media library** | Core Media + Media Library UI | File/Image fields + assets | Media Library + uploads |
| **Taxonomy/tags** | Core taxonomy (vocabularies, terms) | Relational collections | Relations + components |
| **SEO fields** | Metatag module (title, description, canonical, OG) | Custom fields or extension | Custom fields or SEO plugin |
| **Open-source credibility** | Strong, PHP | Strong, Node | Strong, Node |
| **Setup speed** | Heavier (LAMP/stack, learning curve) | Lighter, fast | Lighter, fast |
| **API** | JSON:API / REST (headless) | REST + GraphQL | REST + GraphQL |
| **Hosting** | PHP + DB (e.g. MySQL/Postgres) | Node + DB (e.g. SQLite/Postgres) | Node + DB |

**Recommendation:**

- **If workflow maturity and “serious” editorial process are top priority (and you’re comfortable with Drupal):** **Drupal** is the best fit. It delivers roles, drafts, review, scheduling, revisions, media, taxonomy, and SEO (e.g. Metatag) out of the box or via well-supported modules.
- **If you want lighter/faster setup and can accept some custom or plugin work for scheduling/revisions:** **Directus** or **Strapi** are good alternatives; both can satisfy the checklist with roles, drafts, media, taxonomy, and custom SEO fields, with scheduling/rollback implemented via extensions or small custom logic.

---

## 4. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  CMS (Drupal / Directus / Strapi)                                │
│  - Content types: Blog Post (and optionally Case Study, Page)    │
│  - Workflow: Writer → Editor → Publisher                          │
│  - Draft / Review / Published; scheduled publish; revisions       │
│  - Media library; taxonomy (category/tags); SEO fields            │
│  - REST or GraphQL API (public read for published only)          │
└──────────────────────────────┬──────────────────────────────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
         ▼                     ▼                     ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  Option A:       │  │  Option B:       │  │  Option C:       │
│  Frontend        │  │  Backend proxy   │  │  Build-time      │
│  fetches CMS     │  │  (FastAPI)       │  │  fetch + static  │
│  API directly    │  │  proxies CMS     │  │  (ISR/SSG style) │
└────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
         │                     │                     │
         └─────────────────────┼─────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  ExtensionShield Frontend (React + Vite)                         │
│  - Blog index: list from API or static data                      │
│  - Blog post: /blog/:slug → fetch by slug; 404 if not found      │
│  - SEOHead(title, description, pathname, ogImage, schema)       │
│  - Sitemap: dynamic (API list of published slugs) or build-time  │
└─────────────────────────────────────────────────────────────────┘
```

- **Option A:** Frontend calls CMS API (e.g. `GET /api/blog?status=published`, `GET /api/blog/:slug`) with public read-only key or no auth. Easiest to wire; requires CORS and possibly caching (e.g. CDN) for performance and to avoid overloading CMS.
- **Option B:** FastAPI exposes e.g. `GET /api/content/blog`, `GET /api/content/blog/{slug}` and proxies to CMS. Centralizes auth/caching and hides CMS URL; adds one hop.
- **Option C:** At build time (or on a schedule), a script fetches all published posts from CMS and writes JSON/markdown or triggers a static rebuild; sitemap and routes can stay build-time. Good for maximum performance and simple deploys; publishing has a delay until next build.

Choose one of A/B/C based on how often you publish and whether you need “publish now” vs “publish on next deploy.”

---

## 5. Content Model (Blog Post)

Align with current `blogPosts.js` shape so migration is straightforward. CMS content type should support at least:

| Field | Type | Notes |
|-------|------|--------|
| `slug` | string, unique | URL path: `/blog/{slug}` |
| `title` | string | Page + meta title (or separate SEO title) |
| `description` | string | Meta description (≤160 for SEO) |
| `date` | date/datetime | Display date; can also drive “scheduled at” |
| `category` | taxonomy / single | e.g. Security, Enterprise (current categories) |
| `tags` | taxonomy / multiple | Optional; for filtering and related posts |
| `sections` | repeatable (heading + body) or rich text | Current structure: `[{ heading, body }]` |
| **SEO** | | |
| `meta_title` | string, optional | Override for `<title>` (else use `title`) |
| `meta_description` | string, optional | Override (else use `description`) |
| `canonical_url` | string, optional | Override canonical (else `/blog/{slug}`) |
| `og_image` | media, optional | Override OG image (else site default) |
| **Workflow** | | |
| Status | draft / in_review / published | Only `published` exposed to API |
| `published_at` | datetime, optional | When it went live; can drive “scheduled publish” |
| Revisions | CMS-native | Revisions + rollback in CMS |

Media library is used for `og_image` and any inline images in body/sections if you move to rich text.

---

## 6. Frontend Changes (ExtensionShield)

- **Data layer:**
  - Replace (or parallel-path) `getBlogPostBySlug(slug)` to load from CMS API (or from build-time generated JSON) instead of only `blogPosts.js`.
  - Blog index: fetch list of published posts from API (or use static list at build time).
- **Routing:**
  - Keep single route `path: "/blog/:slug"` with `element: <BlogPostPage />`. Resolve slug dynamically; 404 when not found or not published.
  - No need to add a new route per post in `routes.jsx`; one dynamic route is enough.
- **SEO:**
  - Keep using `SEOHead`. Pass `title` (or `meta_title`), `description` (or `meta_description`), `pathname` (or `canonical_url`), `ogImage` from CMS. Existing `seoUtils` and `SEOHead` already support these.
- **Sitemap:**
  - **Dynamic:** Add an endpoint (frontend or backend) that returns XML sitemap for blog using “list published posts” from CMS; or generate sitemap on a schedule (cron) that calls CMS API and writes `sitemap-blog.xml` (and link it from main sitemap or `robots.txt`).
  - **Build-time:** If using Option C, include published slugs in the existing `generate-sitemap.js` input (e.g. read from a generated `blog-posts.json` or env list).
- **Migration:** Either seed the CMS with existing entries from `blogPosts.js`, or keep current JSON as fallback and only new posts from CMS (feature flag or env to switch source).

---

## 7. Backend (Optional Proxy — Option B)

If you use Option B (FastAPI proxy):

- Add routes, e.g.:
  - `GET /api/content/blog` → proxy to CMS list (published only).
  - `GET /api/content/blog/{slug}` → proxy to CMS by slug (published only).
- Use env for CMS base URL and optional read-only API key; cache responses (in-memory or Redis) with TTL to reduce load on CMS.
- No need to store content in Supabase unless you want a local cache/mirror; CMS remains source of truth.

---

## 8. Implementation Phases

| Phase | Scope | Outcome |
|-------|--------|---------|
| **1. CMS choice & setup** | Install Drupal (or Directus/Strapi); configure content type “Blog Post” with slug, title, description, date, category, tags, sections, SEO fields, media; configure roles (Writer/Editor/Publisher) and workflow (draft → review → published); enable revisions and scheduling. | Editorial team can create and publish content in CMS. |
| **2. Content API** | Expose public read API for published posts only (list + by slug). Optional: FastAPI proxy (Option B). | Frontend (or build script) can fetch published content. |
| **3. Frontend integration** | Switch blog data source from `blogPosts.js` to API (or build-time JSON); keep single `/blog/:slug` route; wire SEO fields from CMS into `SEOHead`; handle 404 and loading states. | Blog is driven by CMS; SEO unchanged or improved. |
| **4. Sitemap & discovery** | Implement dynamic or build-time sitemap for blog slugs; ensure `robots.txt` and main sitemap reference it. | New posts get into sitemap without code changes. |
| **5. Migration & cleanup** | Seed CMS from `blogPosts.js` (or keep JSON as fallback); remove or deprecate static blog route entries for each slug; document editorial process. | Single source of truth; no duplicate content. |
| **6. (Optional) Case studies / pages** | If desired, add “Case Study” or “Page” content types and optional frontend routes that pull from CMS (e.g. `/research/case-studies/:slug`). | Broader content in CMS with same workflow. |

---

## 9. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| CMS downtime or slow response | Cache API responses (CDN or FastAPI cache); optional fallback to static JSON for critical routes. |
| SEO regression | Keep canonical, title, description, OG in control; use same `SEOHead` and test with existing SEO scripts (`seo:test`, etc.). |
| Sitemap out of sync | Prefer dynamic sitemap from CMS or cron-generated sitemap so new posts appear without deploy. |
| Duplicate content during migration | Use 301 redirects from old URLs if you change slugs; keep canonical consistent. |

---

## 10. Success Criteria

- [ ] Writers can create drafts; editors can review; publishers can publish (with optional schedule).
- [ ] Revisions are stored and rollback is possible in the CMS.
- [ ] Media library is used for OG image and inline images (if applicable).
- [ ] Taxonomy (category/tags) is used and visible where needed (e.g. blog index, filters).
- [ ] SEO fields (title, description, canonical, OG) are editable per post and reflected on the site via `SEOHead`.
- [ ] Only published content is visible on the site; sitemap includes all published blog URLs.
- [ ] No regression on existing SEO (titles, meta, canonical, sitemap) for current blog and key pages.

---

## 11. References (Current Codebase)

- Blog data: `frontend/src/data/blogPosts.js`
- Blog UI: `frontend/src/pages/blog/BlogIndexPage.jsx`, `BlogPostPage.jsx`
- Routes: `frontend/src/routes/routes.jsx` (blog segment)
- SEO: `frontend/src/components/SEOHead.jsx`, `frontend/src/utils/seoUtils.js`
- Sitemap: `frontend/scripts/generate-sitemap.js`
- SEO notes: `seo/seo-growth-checklist.md`, `seo/seo-audit.md` — blog currently in JSON, not MD/CMS.
