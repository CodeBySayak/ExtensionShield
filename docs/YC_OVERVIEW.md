# ExtensionShield — Y Combinator Overview

**Enterprise Chrome Extension Security & Governance Platform**

---

## What We Do

ExtensionShield is an enterprise Chrome extension security and governance platform. We give evidence-grade **PASS / FAIL / NEEDS_REVIEW** verdicts using deterministic rules and code-level citations—not subjective scores. Every finding links to file path, line range, code snippet, and policy references.

### Core Value Proposition

- **Static analysis only** — no browsing capture, no runtime monitoring, no agents
- **Evidence-based reports** — ready for audit trails and compliance reviews
- **Deterministic verdicts** — rule evaluation, not black-box risk scores
- **Policy citations** — Chrome Web Store policies and DPDP v0 requirements

---

## Built on Open Source: ThreatXtension

ExtensionShield is built on top of **[ThreatXtension](https://github.com/barvhaim/ThreatXtension)** by Bar Haim & Itzik Chanan. We acknowledge this transparently in:

- **README.md** — direct attribution and link to the upstream repo
- **Methodology page** (`/research/methodology`) — "Powered by ThreatXtension" with GitHub link and contribution link
- **Research / GSoC pages** — credits and links to ThreatXtension

We use ThreatXtension for:

- **Pipeline 1: Security Analysis** — SAST with Semgrep, malware detection, obfuscation detection, 47+ rules
- Schema foundation (scan_results, analytics, statistics migrated from ThreatXtension SQLite)

On top of that, we built:

- **Pipeline 2: Privacy Analysis** — proprietary engine for data collection, third-party tracking, PII, storage audit
- **Pipeline 3: Compliance** — policy engine with rulepacks (ENTERPRISE_GOV_BASELINE, CWS_LIMITED_USE)
- **Scoring Engine v2** — unified Security / Privacy / Governance layers with explainable weights
- **Governance rules engine** — YAML rulepacks, evidence, and citations
- **Human-friendly explanations** — plain-language fallbacks via `LayerHumanizer`

---

## Transparency: How We Score

We publish our methodology and make scoring easy to understand, without technical jargon.

### 1. Methodology Page

Public page at `/research/methodology` explains:

- Three pipelines: Security (ThreatXtension), Privacy, Compliance
- Aggregate formula: **Security × 40% + Privacy × 35% + Compliance × 25%**
- What each pipeline does and which tools it uses
- Open-source credit for ThreatXtension with links

### 2. Scoring Engine (Code-Verified)

From `src/extension_shield/scoring/`:

- **Formula:** Layer Risk `R = Σ(w_i × c_i × s_i) / Σ(w_i × c_i)`, then `score = round(100 × (1 - R))`
- **Weights are versioned** in `weights.py` (e.g., Security: SAST 30%, VirusTotal 15%, Obfuscation 15%, etc.)
- **Hard gates** can override scores (e.g., CRITICAL_SAST, VT_MALWARE, TOS_VIOLATION)
- **Decisions:** ALLOW / NEEDS_REVIEW / BLOCK with reasons
- **Explain module** — per-factor contributions, top contributors, summary

### 3. Human-Friendly Language

`humanize.py` maps technical concepts to plain English:

- **Permissions:** e.g., "can read site cookies", "can access all browser tabs"
- **Host patterns:** e.g., "runs on all websites"
- **Gates:** e.g., "dangerous code pattern found", "flagged by antivirus engines"
- **Factors:** e.g., "code analysis findings", "permission risk assessment"

### 4. Rulepacks

Governance rulepacks are **public YAML** in `governance/rulepacks/`:

- `ENTERPRISE_GOV_BASELINE` — enterprise governance rules (R1–R10)
- `CWS_LIMITED_USE` — Chrome Web Store policy rules
- Each rule: condition, verdict, confidence, recommended_action, citations

---

## Traction & Advisors

- **Demoed to Drupal CTO** — product validated with enterprise open-source leadership
- **Advisor support** — dedicated advisor helping with product and GTM
- **Drupal open-source background** — founder experience in open-source ecosystems (Drupal) shapes our transparency-first approach and non-technical language for scoring

---

## Roadmap: API as a Service & Custom Extensions

### Current API Surface

- `POST /api/scan/trigger` — trigger extension scan
- `POST /api/scan/upload` — upload .crx/.zip
- `GET /api/scan/results/{extension_id}` — full scan results
- `GET /api/scan/report/{extension_id}` — report
- `GET /api/scan/enforcement_bundle/{extension_id}` — enforcement bundle
- `POST /api/enterprise/pilot-request` — enterprise pilot signup
- MCP server for AI/agent integrations (e.g., Cursor, Claude)
- CLI (`make analyze URL=`) for local analysis

### Future Goals

1. **API as a Service** — consumption-based API for SaaS, SIEM, and DevOps pipelines
2. **Custom extensions for enterprises** — validate internally developed and line-of-business extensions
3. **Customizable rulepacks** — tenant-specific policies (context already supports `rulepacks` override in `context_builder.py`)
4. **Custom extensions per business** — support for private/corporate extension catalogs

---

## Product Metrics (from codebase)

| Metric | Value |
|--------|-------|
| Rulepacks | 2 (CWS_LIMITED_USE + ENTERPRISE_GOV_BASELINE) |
| Rules | Dynamic per rulepack (ENTERPRISE_GOV_BASELINE: 10 rules) |
| Evidence | Code snippets, file path, line range per finding |
| Avg scan time | ~45s |
| Scoring version | 2.0.0 |

---

## Trust & Security

- Static analysis only — no browsing capture, no runtime monitoring
- Files processed securely and automatically deleted after 24 hours
- Evidence-based reports — not legal advice
- Open about foundations — ThreatXtension clearly credited

---

## Summary

ExtensionShield is an enterprise Chrome extension security platform built on open-source ThreatXtension. We are transparent about our methodology and scoring, use plain-language explanations, and deliver deterministic, evidence-backed verdicts. With demos to leaders like the Drupal CTO and advisor support, we are focused on turning our API into a service and extending coverage to custom and enterprise extensions.
