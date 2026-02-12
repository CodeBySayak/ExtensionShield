# Scan Results & Quick Summary Architecture

This document describes the implemented architecture for the Scan Results page: **Security / Privacy / Governance** layer modals, **Quick Summary** panel, and the **LLM-powered unified summary** pipeline.

---

## 1. Overview

| Area | Purpose |
|------|---------|
| **Scan Results Page** | Displays extension scan outcome: hero (name, icon, overall score), three layer score cards, Quick Summary, and optional panels. |
| **Layer Modals** | One modal per layer (Security, Privacy, Governance) opened from the score cards; shows score, one-liner, and risk breakdown. |
| **Quick Summary** | Single consumer-facing summary: headline + narrative (or legacy verdict/reasons/access/action). |
| **Unified Summary (LLM)** | Backend generates one cohesive narrative from all findings; frontend displays it in the Quick Summary panel. |

---

## 2. Data Flow (High Level)

```
Scan Pipeline
    → ScoringEngine (scoring_v2: security_layer, privacy_layer, governance_layer)
    → LayerDetailsGenerator (LLM) → layer_details (one_liner, key_points, what_to_watch per layer)
    → Report View Model Builder
        → build_consumer_summary()     → consumer_summary (verdict, reasons, access, action)
        → build_unified_consumer_summary() → unified_summary (headline, narrative, tldr, concerns, recommendation)
    → report_view_model (JSON)
        → Frontend: normalizeScanResult() → ReportViewModel
        → SummaryPanel: prefers unified_summary.narrative, falls back to consumer_summary or highlights
        → LayerModal: receives factorsByLayer[layer], layerDetails, score, band
```

---

## 3. Backend Architecture

### 3.1 Report View Model

**File:** `src/extension_shield/core/report_view_model.py`

The report view model is the single payload sent to the frontend. It includes:

| Key | Source | Purpose |
|-----|--------|---------|
| `meta` | scan metadata | Extension id, name, scan id. |
| `scorecard` | scoring_result | Overall score, score_label, confidence, one_liner. |
| `evidence` | SignalPack + analysis | host_access_summary, capability_flags, permissions_summary, sast_summary, etc. |
| `layer_details` | LayerDetailsGenerator (LLM) or LayerHumanizer | Per-layer one_liner, key_points, what_to_watch. |
| `highlights` | SummaryGenerator / scorecard | why_this_score, what_to_watch (used by legacy consumer_summary). |
| `consumer_summary` | build_consumer_summary() | Verdict, reasons, access, action (deterministic). |
| `unified_summary` | build_unified_consumer_summary() | Headline, narrative, tldr, concerns, recommendation (LLM or fallback). |

### 3.2 Scoring V2 Structure

**Files:** `src/extension_shield/scoring/models.py`, `scoring/engine.py`, `scoring/normalizers.py`

- **ScoringResult** holds:
  - `security_layer`, `privacy_layer`, `governance_layer` (each **LayerScore** with `score`, `factors[]`, `risk_level`, etc.).
  - `overall_score`, `decision` (ALLOW / NEEDS_REVIEW / BLOCK), `reasons`, `hard_gates_triggered`.
- Each **LayerScore** has a list of **FactorScore** (name, severity, confidence, weight, details, evidence_ids).
- Factor names (aligned with frontend `FACTOR_HUMAN`):
  - **Security:** SAST, VirusTotal, Obfuscation, Manifest, ChromeStats, Webstore, Maintenance.
  - **Privacy:** PermissionsBaseline, PermissionCombos, NetworkExfil, CaptureSignals.
  - **Governance:** ToSViolations, Consistency, DisclosureAlignment.

The API serialization uses `model_dump_for_api()`, which exposes `security_layer`, `privacy_layer`, `governance_layer` as dictionaries with `factors` arrays (no `layers` wrapper).

### 3.3 Unified Consumer Summary (Quick Summary LLM)

**Function:** `build_unified_consumer_summary()` in `report_view_model.py`

**Purpose:** Produce one **headline** and one **narrative** that weave together:

1. What the extension can do (from humanized permissions and host access).
2. Key concerns from Security, Privacy, and Governance findings.
3. One clear recommendation.

**Inputs used:**

- `report_view_model`: scorecard, evidence, layer_details, highlights.
- `scoring_v2`: `security_layer`, `privacy_layer`, `governance_layer` (factors with severity ≥ 0.3), `decision`, `hard_gates_triggered`.
- `analysis_results`: e.g. permissions_analysis.
- `manifest`: permissions, host_permissions.
- `extension_name`.

**Findings aggregation:**

- **From layer_details:** Each layer’s `key_points` → security_findings, privacy_findings, governance_findings.
- **From scoring_v2:** Each layer’s `factors` (with `severity >= 0.3`); factor name + details.description → appended to the corresponding layer’s findings list.
- **What It Can Do:** `_build_what_it_can_do(manifest, analysis_results, host_access)` → humanized list (uses `PERMISSION_TO_PLAIN` and `LayerHumanizer.HOST_EXPLANATIONS`).
- **All key findings:** security_findings[:3] + privacy_findings[:3] + governance_findings[:3], plus hard_gates_triggered[:2] prepended.

**Prompt:** `consumer_summary_unified` in `src/extension_shield/llm/prompts/summary_generation.yaml`

- **Template format:** Jinja2 (`{{ variable }}`). The code uses `PromptTemplate(..., template_format="jinja2")` so variables are substituted correctly.
- **Variables passed:** extension_name, score, score_label, security_score, privacy_score, governance_score, decision, host_access_summary_json, permissions_json, what_it_can_do_json, key_findings_json, security_findings_json, privacy_findings_json, governance_findings_json.
- **Output schema:** `headline` (max 100 chars), `narrative` (max 400 chars). Optional: tldr, concerns, recommendation for fallback display.

**LLM invocation:** `invoke_with_fallback()` from `extension_shield.llm.clients.fallback` with `LLM_MODEL` (default `gpt-4o`). Provider chain is configurable (e.g. GROQ → WATSONX → OPENAI).

**Fallback:** If the LLM call fails, `_fallback_unified_consumer_summary()` builds a deterministic headline, tldr, concerns (from layer_details key_points or highlights.why_this_score), and recommendation, and concatenates them into a single `narrative` string so the frontend can still show one block.

### 3.4 Consumer Summary (Legacy)

**Function:** `build_consumer_summary()` in `report_view_model.py`

Deterministic summary: verdict (from score_label/one_liner), reasons (highlights.why_this_score or layer_details key_points), access (from evidence.host_access_summary and capability_flags), action (highlights.what_to_watch or score-based default). Used when the frontend does not have unified_summary or when unified_summary has no narrative.

### 3.5 Layer Details (Per-Layer LLM)

**File:** `src/extension_shield/core/layer_details_generator.py`  
**Prompt:** `layer_details_generation` in `src/extension_shield/llm/prompts/layer_details_generation.yaml`

Generates for each of security, privacy, governance:

- `one_liner` (max 150 chars)
- `key_points` (0–4 items, max 120 chars each)
- `what_to_watch` (0–3 items, max 120 chars each)

Template uses Jinja2; variables include layer scores, risk levels, factors JSON, gates JSON, permissions_summary, host_access_summary, sast_result, network_evidence, manifest.

---

## 4. Frontend Architecture

### 4.1 Normalization

**File:** `frontend/src/utils/normalizeScanResult.ts`

- **normalizeScanResult(raw):** Builds a single **ReportViewModel** from raw scan result.
- **Scores:** From `scoring_v2` (security_layer, privacy_layer, governance_layer, overall_score, decision, reasons).
- **factorsByLayer:** `getLayerFactors(scoringV2.security_layer)` (and same for privacy, governance) → array of FactorVM (name, severity, confidence, weight, riskContribution, evidenceIds, details).
- **keyFindings:** From scoring_v2 and raw (e.g. SAST/engine findings).
- **permissions:** From raw (buildPermissions).
- **report_view_model** is kept on raw for SummaryPanel: `rawScanResult?.report_view_model?.unified_summary` and `consumer_summary`.

### 4.2 Scan Results Page

**File:** `frontend/src/pages/scanner/ScanResultsPageV2.jsx`

- Uses `normalizeScanResultSafe(raw)` to get view model.
- Renders:
  - Hero (icon, name, overall score dial).
  - Three **ReportScoreCard**s (Security, Privacy, Governance) with score, band, contributors; onClick opens the corresponding **LayerModal**.
  - **SummaryPanel** with scores, factorsByLayer, rawScanResult, keyFindings.
  - One **LayerModal** per layer when `layerModal.layer === 'security' | 'privacy' | 'governance'`; each receives factors from `factorsByLayer[layer]`, layerDetails from `report_view_model.layer_details`, score/band, keyFindings (deduped by layer), gateResults, layerReasons.

### 4.3 Layer Modal

**File:** `frontend/src/components/report/LayerModal.jsx`  
**Styles:** `LayerModal.scss`

**Current sections (no Key Findings, What It Can Do, or What to Watch in modal):**

| Section | Data | Notes |
|---------|------|--------|
| Header | score, band, layer config | Title, icon, mini score ring (SVG), score text, band label. |
| One-liner | layerDetails[layer].one_liner | Or fallback tagline from LAYER_CONFIG. |
| Risk Breakdown | factors (grouped by category) | Visual gauge cards: factor icon, gauge bar (severity), label, description, risk badge (High/Medium/Low/Clear). |

**Data received:** open, onClose, layer, score, band, factors, keyFindings, gateResults, layerReasons, layerDetails, onViewEvidence.  
**Factor display:** Factors are humanized via `FACTOR_HUMAN` (label, icon, category, desc) and grouped by category; categories use `CATEGORY_LABELS`. All factors that contribute to the layer score are shown in the Risk Breakdown (no section removed from score calculation).

### 4.4 Quick Summary Panel

**File:** `frontend/src/components/report/SummaryPanel.jsx`  
**Styles:** `SummaryPanel.scss`

**Priority order:**

1. **Unified summary** (`report_view_model.unified_summary`):
   - If `narrative` is present: show **headline** + **narrative** only (single flowing text; no separate bullets).
   - If no narrative: show headline, then tldr, Key Concerns (unified_summary.concerns or engineConcerns), and recommendation.
2. **Consumer summary** (`report_view_model.consumer_summary`): Verdict, Why This Score (reasons), What It Can Access, What to Do.
3. **Legacy highlights:** oneLiner + Key Concerns (engineConcerns from keyFindings, or keyPoints from normalizeHighlights).

**engineConcerns:** Derived from `keyFindings` (high/medium severity), used when unified summary has no narrative or in legacy path.

---

## 5. Key Design Decisions

- **Single narrative in Quick Summary:** The LLM is instructed to produce one headline and one narrative that combine capabilities, concerns, and recommendation to avoid fragmented “AI-looking” sections. “What It Can Do” is not duplicated in the modal; it is included in the Quick Summary narrative via the prompt.
- **No Key Findings / What to Watch in modal:** These were removed from the modal to avoid redundancy with the Quick Summary and to keep the modal focused on the score and risk breakdown.
- **Findings for LLM:** All findings that feed the Quick Summary come from (1) layer_details.key_points, (2) scoring_v2 layer factors (security_layer, privacy_layer, governance_layer) with severity ≥ 0.3, and (3) hard_gates_triggered. Layer scores and decision are also passed so the tone matches the overall result.
- **Jinja2 for prompts:** YAML prompts use `{{ variable }}`. The code uses `PromptTemplate(..., template_format="jinja2")` in both summary and layer-details generation so placeholders are correctly replaced.
- **Fallback behavior:** If the unified-summary LLM fails, a deterministic narrative is built from tldr + concerns + recommendation and returned with `source: "fallback"` so the UI still shows a single summary block.

---

## 6. File Reference

| Component | File(s) |
|-----------|--------|
| Report view model & unified summary | `src/extension_shield/core/report_view_model.py` |
| Summary prompt | `src/extension_shield/llm/prompts/summary_generation.yaml` |
| Layer details prompt | `src/extension_shield/llm/prompts/layer_details_generation.yaml` |
| LLM invocation | `src/extension_shield/llm/clients/fallback.py` |
| Scoring models & API dump | `src/extension_shield/scoring/models.py` |
| Normalization | `frontend/src/utils/normalizeScanResult.ts` |
| Scan results page | `frontend/src/pages/scanner/ScanResultsPageV2.jsx` |
| Layer modal | `frontend/src/components/report/LayerModal.jsx`, `LayerModal.scss` |
| Quick Summary panel | `frontend/src/components/report/SummaryPanel.jsx`, `SummaryPanel.scss` |

---

## 7. Related Docs

- **SCAN_RESULTS_MODAL_DATA_SPEC.md** – Data spec for the scan results page and modals (may describe older five-section modal; current modal has three sections as above).
- **YC_OVERVIEW.md** – Product/context overview.
