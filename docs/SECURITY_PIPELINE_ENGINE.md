# ExtensionShield Security Pipeline & Scoring Engine — Comprehensive Documentation

This document is the **single reference** for the entire security pipeline: workflow, three-layer scoring architecture, LLM usage, report view model, and how each section feeds the scan results UI. Use it for context when working on any part of the engine.

**Related docs:**  
[SECURITY_PRIVACY_GOVERNANCE_DATA_SOURCES.md](./SECURITY_PRIVACY_GOVERNANCE_DATA_SOURCES.md) (where each data & summary comes from) · [SCAN_RESULTS_AND_SCORING_ENGINE.md](./SCAN_RESULTS_AND_SCORING_ENGINE.md) (UI cards & formulas) · [SCAN_RESULTS_ARCHITECTURE.md](./SCAN_RESULTS_ARCHITECTURE.md) (Quick Summary & LLM flow) · [SCAN_RESULTS_MODAL_DATA_SPEC.md](./SCAN_RESULTS_MODAL_DATA_SPEC.md) (Layer modal data) · [SCORING_ENGINE_AND_WORKFLOW_ANALYSIS.md](./SCORING_ENGINE_AND_WORKFLOW_ANALYSIS.md) (detailed engine analysis) · [SCORING_WEIGHTS_AND_ANALYSIS.md](./SCORING_WEIGHTS_AND_ANALYSIS.md) (weights & factors) · [qa_scoring_overrides_and_gates.md](./qa_scoring_overrides_and_gates.md) (gates & coverage cap) · [qa_crxplorer_comparison.md](./qa_crxplorer_comparison.md) (competitor comparison)

---

## 1. Pipeline Overview: Three Layers

| Layer | Name | Purpose | Primary code |
|-------|------|---------|---------------|
| **Pipeline 1** | Signal extraction (Layer 0) | Normalize all analyzer outputs into one structure | `SignalPackBuilder`, `tool_adapters.py`, `signal_pack.py` |
| **Pipeline 2** | Risk scoring (Layer 1) | Compute Security / Privacy / Governance scores and decision from signals | `ScoringEngine`, `normalizers.py`, `gates.py`, `weights.py` |
| **Pipeline 3** | Decision, report & LLM humanization | Rules engine, report view model, layer details, unified summary | `governance_nodes.py`, `report_view_model.py`, `LayerDetailsGenerator`, LLM clients |

**Single source of truth for score and decision:** `ScoringEngine.calculate_scores()` in `src/extension_shield/scoring/engine.py`. The API and frontend consume `governance_bundle.scoring_v2`; there is no client-side score computation.

---

## 2. End-to-End Workflow (Where Each Pipeline Runs)

The workflow is a **LangGraph** linear chain. Entry: `extension_path_routing_node`; exit: `cleanup_node`.

| Order | Node | File | What it does | Pipeline |
|-------|------|------|----------------|----------|
| 1 | `extension_path_routing_node` | `workflow/nodes.py` | Routes by input: extension ID → chromestats downloader; CWS URL → metadata; local CRX → downloader; else END (failed) | — |
| 2 | `extension_metadata_node` | `workflow/nodes.py` | Fetches CWS metadata; optionally fetches chrome-stats by extension ID | — |
| 3 | `chromestats_downloader_node` | `workflow/nodes.py` | Downloads from chrome-stats by ID; extracts CRX | — |
| 4 | `extension_downloader_node` | `workflow/nodes.py` | Downloads from CWS or extracts local CRX | — |
| 5 | `manifest_parser_node` | `workflow/nodes.py` | Parses `manifest.json` → `manifest_data` | — |
| 6 | `extension_analyzer_node` | `workflow/nodes.py` | **ExtensionAnalyzer.analyze()** — runs all analyzers (SAST, VT, permissions, entropy, webstore, chromestats) → `analysis_results` | Feeds Pipeline 1 |
| 7 | `summary_generation_node` | `workflow/nodes.py` | **LLM:** Executive summary (SummaryGenerator) | Pipeline 3 (LLM) |
| 8 | `impact_analysis_node` | `workflow/nodes.py` | **LLM:** Impact analysis buckets (ImpactAnalyzer) | Pipeline 3 (LLM) |
| 9 | `privacy_compliance_node` | `workflow/nodes.py` | **LLM:** Privacy/compliance snapshot (PrivacyComplianceAnalyzer) | Pipeline 3 (LLM) |
| 10 | **`governance_node`** | **`workflow/governance_nodes.py`** | **Pipeline 1 + 2:** SignalPackBuilder → ScoringEngine. **Pipeline 3 (legacy):** Facts, evidence, signals, rules engine, report. **No LLM here** — report_view_model (including LLM) is built later in the API. | Pipeline 1, 2, 3 (legacy) |
| 11 | `cleanup_node` | `workflow/nodes.py` | Collects file list; removes downloaded CRX; → END | — |

**State:** `WorkflowState` in `workflow/state.py` holds `workflow_id`, `chrome_extension_path`, `extension_dir`, `manifest_data`, `analysis_results`, `executive_summary`, `impact_analysis`, `privacy_compliance`, `governance_bundle`, etc.

**Where `report_view_model` is built:** Not in the graph. The API (`api/main.py`) calls `build_report_view_model_safe()` (in `api/payload_helpers.py`) after the workflow returns. That builds `report_view_model` (including **Layer Details LLM** and **Unified Summary LLM**), then attaches it to the scan results payload returned to the client.

---

## 3. Pipeline 1 — Signal Extraction (Layer 0)

**Purpose:** Turn raw `analysis_results`, `metadata`, and `manifest` into a single **SignalPack** so the scoring engine has one normalized input.

### 3.1 Where it runs

- **File:** `governance/tool_adapters.py` — class `SignalPackBuilder`
- **Invoked:** Inside `governance_node`:  
  `signal_pack = signal_pack_builder.build(scan_id, analysis_results, metadata, manifest, extension_id)`

### 3.2 Inputs

- `analysis_results`: Output of `ExtensionAnalyzer.analyze()` (SAST, VirusTotal, permissions, entropy, webstore, chromestats, etc.)
- `metadata`: From extension metadata node (e.g. CWS/chrome-stats)
- `manifest`: Parsed `manifest_data` from manifest_parser_node

### 3.3 Process

- **SignalPackBuilder** instantiates adapters and calls `adapter.adapt(...)` for each, mutating one **SignalPack**.
- **Adapters** (in `tool_adapters.py`):
  - **SastAdapter** → `sast` (SastSignalPack: deduped_findings, files_scanned, confidence)
  - **VirusTotalAdapter** → `virustotal` (VirusTotalSignalPack: malicious_count, suspicious_count, total_engines, enabled)
  - **EntropyAdapter** → `entropy` (EntropySignalPack: obfuscated_count, suspicious_count, files_analyzed)
  - **WebstoreStatsAdapter** → `webstore_stats` (installs, rating_avg, last_updated, has_privacy_policy)
  - **WebstoreReviewsAdapter** → webstore reviews
  - **PermissionsAdapter** → `permissions` (api_permissions, high_risk_permissions, unreasonable_permissions, has_broad_host_access)
  - **ChromeStatsAdapter** → `chromestats` (enabled, total_risk_score, risk_indicators)
  - **NetworkAdapter** → `network` (enabled, domains, suspicious_flags, confidence)
- **Evidence:** Each adapter can append to `signal_pack.evidence` (ToolEvidence list). Evidence ID pattern: `tool:<toolname>:<hash>`.

### 3.4 Output

- **SignalPack** (`governance/signal_pack.py`): One object with `sast`, `virustotal`, `entropy`, `webstore_stats`, `permissions`, `chromestats`, `network`, `evidence`. This is the **only** input to the scoring engine (plus optional `manifest` and `user_count`).

### 3.5 Key files

| File | Role |
|------|------|
| `governance/tool_adapters.py` | SignalPackBuilder, all adapters |
| `governance/signal_pack.py` | SignalPack and per-tool signal models |

---

## 4. Pipeline 2 — Risk Scoring (Layer 1)

**Purpose:** From SignalPack (and manifest/user_count), compute Security, Privacy, and Governance layer scores, apply gates and coverage cap, and produce overall score and decision (ALLOW / NEEDS_REVIEW / BLOCK).

### 4.1 Where it runs

- **File:** `scoring/engine.py` — class `ScoringEngine`
- **Invoked:** Inside `governance_node`:  
  `scoring_engine = ScoringEngine(weights_version="v1")`  
  `scoring_result = scoring_engine.calculate_scores(signal_pack=signal_pack, manifest=manifest_data, user_count=user_count)`

### 4.2 High-level steps (in order)

1. **Normalize signals to factors** — For each layer, convert SignalPack fields into factors with `severity` [0,1] and `confidence` [0,1] using `scoring/normalizers.py`.
2. **Compute layer scores** — Confidence-weighted risk per layer:  
   `R = Σ(w_i × c_i × s_i) / Σ(w_i × c_i)`; `score = round(100 × (1 - R))`.
3. **Evaluate hard gates** — Can force BLOCK or WARN regardless of score (`scoring/gates.py`).
4. **Apply gate penalties** — Subtract points from layer scores (per-gate base penalty × decision multiplier × confidence); floor at 0.
5. **Compute overall score** — `overall = 0.5×security + 0.3×privacy + 0.2×governance` (after penalties).
6. **Apply coverage cap** — If SAST has no coverage and overall > 80 → cap overall at 80 and force NEEDS_REVIEW.
7. **Determine decision** — Priority: blocking gate → BLOCK; security &lt; 30 or overall &lt; 30 → BLOCK; warning gate → NEEDS_REVIEW; security &lt; 60 or overall &lt; 60 → NEEDS_REVIEW; else ALLOW.

### 4.3 Weights (v1) — Full calculation weights

**Source:** `scoring/weights.py`. Preset: `v1` (DEFAULT_PRESET).

**Formulas (for reference):**

- **Layer risk (per layer):**  
  `R = Σ(w_i × c_i × s_i) / Σ(w_i × c_i)`  
  where `w_i` = factor weight below, `c_i` = confidence [0,1], `s_i` = severity [0,1].
- **Layer score:**  
  `layer_score = round(100 × (1 - R))` (0–100).
- **Overall score:**  
  `overall_score = security_score × W_sec + privacy_score × W_priv + governance_score × W_gov`  
  using the layer weights below (after gate penalties and coverage cap).

**Layer → overall (contribution to final score)**  
Sum = 1.0.

| Layer     | Weight | %   | Role                |
|-----------|--------|-----|---------------------|
| Security  | 0.50   | 50% | Primary             |
| Privacy   | 0.30   | 30% | Secondary           |
| Governance| 0.20   | 20% | Policy/compliance   |

**Security layer factor weights**  
Sum = 1.0. Each factor’s **effective weight on overall** = 0.50 × factor weight.

| Factor      | Weight | %   | Effective on overall | Description |
|-------------|--------|-----|----------------------|-------------|
| SAST        | 0.30   | 30% | 0.15 (15%)          | Static analysis findings |
| VirusTotal  | 0.15   | 15% | 0.075 (7.5%)        | Malware detection |
| Obfuscation | 0.15   | 15% | 0.075 (7.5%)        | Code obfuscation |
| Manifest    | 0.10   | 10% | 0.05 (5%)           | Manifest/CSP/broad host |
| ChromeStats | 0.10   | 10% | 0.05 (5%)           | Behavioral threat intel |
| Webstore    | 0.10   | 10% | 0.05 (5%)           | Store reputation |
| Maintenance | 0.10   | 10% | 0.05 (5%)           | Update freshness |

**Privacy layer factor weights**  
Sum = 1.0. Effective on overall = 0.30 × factor weight.

| Factor              | Weight | %   | Effective on overall | Description |
|---------------------|--------|-----|----------------------|-------------|
| PermissionsBaseline | 0.25   | 25% | 0.075 (7.5%)        | High-risk / unreasonable permission count |
| PermissionCombos    | 0.25   | 25% | 0.075 (7.5%)        | Dangerous permission combinations |
| NetworkExfil       | 0.35   | 35% | 0.105 (10.5%)       | Network exfiltration patterns |
| CaptureSignals     | 0.15   | 15% | 0.045 (4.5%)        | Screenshot / tab capture |

**Governance layer factor weights**  
Sum = 1.0. Effective on overall = 0.20 × factor weight.

| Factor               | Weight | %   | Effective on overall | Description |
|----------------------|--------|-----|----------------------|-------------|
| ToSViolations        | 0.50   | 50% | 0.10 (10%)           | ToS / policy violations |
| Consistency          | 0.30   | 30% | 0.06 (6%)            | Claimed vs actual behavior |
| DisclosureAlignment  | 0.20   | 20% | 0.04 (4%)            | Privacy policy vs data collection |

### 4.4 Normalizers (severity & confidence)

- **File:** `scoring/normalizers.py`. All factors get severity and confidence in [0, 1].
- **Security:** SAST (weighted finding sum → saturation), VirusTotal (malicious/suspicious → bands), Obfuscation (entropy signals), Manifest (CSP, MV2, broad host), ChromeStats, Webstore, Maintenance (days since update).
- **Privacy:** PermissionsBaseline, PermissionCombos, NetworkExfil (domain risk + suspicious flags), CaptureSignals.
- **Governance:** Computed inside the engine in `_compute_governance_factors()`: ToSViolations (prohibited perms, travel-docs risk), Consistency (claimed vs risk), DisclosureAlignment (policy vs data).

### 4.5 Hard gates

- **File:** `scoring/gates.py` — class `HardGates`.
- **Order:** VT_MALWARE → CRITICAL_SAST → TOS_VIOLATION → PURPOSE_MISMATCH → SENSITIVE_EXFIL.
- **Gate list:** See [qa_scoring_overrides_and_gates.md](./qa_scoring_overrides_and_gates.md) and [SCORING_WEIGHTS_AND_ANALYSIS.md](./SCORING_WEIGHTS_AND_ANALYSIS.md) for condition and penalty tables (e.g. CRITICAL_SAST → security −50, VT_MALWARE → security −45, TOS_VIOLATION → governance −60).

### 4.6 Output

- **ScoringResult** (`scoring/models.py`): `security_score`, `privacy_score`, `governance_score`, `overall_score`, `decision`, `reasons`, `security_layer` / `privacy_layer` / `governance_layer` (each with `factors`), `hard_gates_triggered`, `base_overall`, `gate_penalty`, `gate_reasons`, `coverage_cap_applied`, `coverage_cap_reason`, etc.
- This is serialized into `governance_bundle.scoring_v2` in `governance_nodes.py` (including `security_layer`, `privacy_layer`, `governance_layer` via `model_dump_for_api()`, plus `explanation` and `gate_results`).

### 4.7 Key files

| File | Role |
|------|------|
| `scoring/engine.py` | ScoringEngine, layer/overall score, gates, decision, coverage cap |
| `scoring/weights.py` | Layer and factor weights (v1) |
| `scoring/normalizers.py` | Severity/confidence per factor from SignalPack |
| `scoring/gates.py` | Hard gate conditions and penalties |
| `scoring/models.py` | FactorScore, LayerScore, ScoringResult |
| `scoring/explain.py` | Explanation builder for UI/API |

---

## 5. Pipeline 3 — Decision, Report & LLM Humanization

This section covers: (1) legacy rules engine and report inside the workflow, (2) where **report_view_model** is built (API), and (3) **every place the LLM is invoked** and how fallbacks work.

### 5.1 Legacy stages (inside governance_node)

After Layer 0 and Layer 1, `governance_node` still runs:

- **Stage 2:** FactsBuilder → facts
- **Stage 3:** EvidenceIndexBuilder → evidence_index
- **Stage 4:** SignalExtractor (legacy + from SignalPack) → merged signals
- **Stage 5:** StoreListingExtractor → store_listing
- **Stage 6:** ContextBuilder → context
- **Stage 7:** RulesEngine → rule_results
- **Stage 8:** ReportGenerator → report (governance report)

The **decision** shown to the API as the single source of truth is **V2**: `scoring_result.decision`. Legacy report and rules are kept for compatibility and serialized in `governance_bundle`.

### 5.2 Where report_view_model is built

- **Not in the workflow.** After `graph.ainvoke()` returns, the API uses the final state to build the response.
- **Entry point:** `api/main.py` → calls `build_report_view_model_safe()` from `api/payload_helpers.py`.
- **Full builder:** `core/report_view_model.py` → `build_report_view_model()`. This function:
  - Takes pipeline outputs (scan payload with `governance_bundle.scoring_v2`, `analysis_results`, `manifest`, etc.).
  - Optionally reuses or calls **SummaryGenerator**, **ImpactAnalyzer**, **PrivacyComplianceAnalyzer** (only if not already in state, and only if `skip_llm=False`).
  - Calls **LayerDetailsGenerator** (LLM) or **LayerHumanizer.generate_layer_details_fallback()** (deterministic) → `layer_details`.
  - Calls **build_unified_consumer_summary()** (LLM) or **build_consumer_summary()** (deterministic) → `unified_summary` / `consumer_summary`.
  - Assembles `report_view_model` (meta, scorecard, evidence, layer_details, highlights, consumer_summary, unified_summary, etc.).

So **Pipeline 3 “report & LLM”** runs partly in the **workflow nodes** (summary, impact, privacy compliance) and partly **in the API** when building `report_view_model` (layer details + unified summary).

### 5.3 LLM invocation map

| LLM use | File | When | Fallback |
|--------|------|------|----------|
| **Executive summary** | `core/summary_generator.py` | `summary_generation_node` | `_fallback_executive_summary()` in report_view_model |
| **Impact analysis** | `core/impact_analyzer.py` | `impact_analysis_node` | `_fallback_impact_from_capability_flags()` |
| **Privacy compliance** | `core/privacy_compliance_analyzer.py` | `privacy_compliance_node` | Built-in deterministic fallback in analyzer |
| **Layer details** (one_liner, key_points, what_to_watch per layer) | `core/layer_details_generator.py` | Inside `build_report_view_model()` | `LayerHumanizer.generate_layer_details_fallback()` in `scoring/humanize.py` |
| **Unified consumer summary** (headline + narrative) | `core/report_view_model.py` → `build_unified_consumer_summary()` | Inside `build_report_view_model()` | `_fallback_unified_consumer_summary()` (deterministic narrative from tldr/concerns/recommendation) |

### 5.4 How the LLM is called (shared pattern)

- **Client:** `llm/clients/fallback.py` — `invoke_with_fallback()`. Tries providers in order from `LLM_FALLBACK_CHAIN` (or default: GROQ → WATSONX → OPENAI). On failure, next provider; if all fail, raises `LLMFallbackError`.
- **Prompts:** YAML in `llm/prompts/` (e.g. `summary_generation.yaml`, `layer_details_generation.yaml`, `summary_generation.yaml` for unified summary). Loaded via `get_prompts(...)`. Templates use **Jinja2** (`{{ variable }}`); code uses `PromptTemplate(..., template_format="jinja2")`.
- **Model:** `LLM_MODEL` env (e.g. `gpt-4o` for summary/layer-details; some analyzers use different defaults).
- **Validation:** Some flows use `llm/validators.py` to check LLM output against authoritative signals (e.g. one_liner must not contradict score_label).

### 5.5 Layer details LLM (Pipeline 3, per-layer copy)

- **Class:** `LayerDetailsGenerator` in `core/layer_details_generator.py`.
- **Prompt:** `layer_details_generation` in `llm/prompts/layer_details_generation.yaml`.
- **Inputs:** ScoringResult (scores, risk levels, factors per layer), gate_results, permissions_summary, host_access_summary, sast_result, network_evidence, manifest (injected as JSON/blocks).
- **Output:** For each of security, privacy, governance: `one_liner` (≤150 chars), `key_points` (0–4, ≤120 chars), `what_to_watch` (0–3, ≤120 chars). Same schema as fallback so the frontend does not change.
- **Invoked:** From `build_report_view_model()`; on LLM failure, `LayerHumanizer.generate_layer_details_fallback()` is used.

### 5.6 Unified consumer summary LLM (Pipeline 3, Quick Summary)

- **Function:** `build_unified_consumer_summary()` in `core/report_view_model.py`.
- **Prompt:** `consumer_summary_unified` in `llm/prompts/summary_generation.yaml`.
- **Inputs:** extension_name, score, score_label, layer scores, decision, host_access_summary, permissions, what_it_can_do, key_findings, security/privacy/governance findings (from layer_details + scoring_v2 factors with severity ≥ 0.3).
- **Output:** headline (≤100 chars), narrative (≤400 chars); optional tldr, concerns, recommendation.
- **Invoked:** From `build_report_view_model()`; on failure, `_fallback_unified_consumer_summary()` builds a single narrative from tldr + concerns + recommendation.

### 5.7 Key files (Pipeline 3)

| File | Role |
|------|------|
| `workflow/governance_nodes.py` | Runs Pipeline 1 & 2; legacy stages 2–8; builds governance_bundle |
| `core/report_view_model.py` | build_report_view_model, build_unified_consumer_summary, build_consumer_summary, fallbacks |
| `core/layer_details_generator.py` | Layer details LLM |
| `scoring/humanize.py` | LayerHumanizer (layer details fallback), GATE_EXPLANATIONS, etc. |
| `core/summary_generator.py` | Executive summary LLM |
| `core/impact_analyzer.py` | Impact analysis LLM |
| `core/privacy_compliance_analyzer.py` | Privacy compliance LLM |
| `llm/clients/fallback.py` | invoke_with_fallback, LLMFallbackError |
| `llm/prompts/*.yaml` | Prompt templates (Jinja2) |
| `api/payload_helpers.py` | build_report_view_model_safe, upgrade logic for legacy payloads |

---

## 6. Data Flow: From Scan to UI

```
User requests scan (extension ID / CWS URL / CRX)
    → Workflow: routing → metadata/download → manifest → extension_analyzer_node
    → analysis_results
    → summary_generation_node (LLM) → executive_summary
    → impact_analysis_node (LLM) → impact_analysis
    → privacy_compliance_node (LLM) → privacy_compliance
    → governance_node:
        → Pipeline 1: SignalPackBuilder.build() → SignalPack
        → Pipeline 2: ScoringEngine.calculate_scores(signal_pack, manifest, user_count) → ScoringResult
        → Legacy: facts, evidence, signals, rules, report
        → governance_bundle (includes scoring_v2, signal_pack, report, etc.)
    → cleanup_node → END

API (after workflow):
    → build_report_view_model_safe(payload)
        → build_report_view_model():
            → LayerDetailsGenerator.generate() or LayerHumanizer.generate_layer_details_fallback() → layer_details
            → build_unified_consumer_summary() or _fallback_unified_consumer_summary() → unified_summary
            → build_consumer_summary() → consumer_summary
        → payload["report_view_model"] = report_view_model
    → Response: scan_results with scoring_v2 + report_view_model

Frontend (/scan/results/:scanId):
    → GET /api/scan/results/{id} → raw payload
    → normalizeScanResult(raw) → ReportViewModel (scores, factorsByLayer, keyFindings, etc.)
    → ScanResultsPageV2: DonutScore(scores.overall), ResultsSidebarTile × 3 (Security, Privacy, Governance)
    → SummaryPanel: unified_summary.narrative or consumer_summary or highlights
    → LayerModal (per layer): factorsByLayer[layer], layerDetails[layer].one_liner, status badges (No Issues / Issues Found)
```

---

## 7. Section Index (Where to Work on What)

| Section | Purpose | Main files |
|---------|---------|------------|
| **Workflow graph & nodes** | Add/change scan steps, routing, analyzers | `workflow/graph.py`, `workflow/nodes.py`, `workflow/state.py` |
| **Signal extraction (Layer 0)** | Change how tool outputs become signals; add adapters | `governance/tool_adapters.py`, `governance/signal_pack.py` |
| **Scoring (Layer 1)** | Weights, formulas, factors, gates, decision, coverage cap | `scoring/engine.py`, `scoring/weights.py`, `scoring/normalizers.py`, `scoring/gates.py`, `scoring/models.py` |
| **Governance node** | Wire Pipeline 1 & 2; legacy stages; shape of governance_bundle | `workflow/governance_nodes.py` |
| **Report view model** | What the UI gets: meta, scorecard, layer_details, unified_summary | `core/report_view_model.py`, `api/payload_helpers.py` |
| **Layer details (modal copy)** | Per-layer one_liner, key_points, what_to_watch; LLM vs fallback | `core/layer_details_generator.py`, `scoring/humanize.py`, `llm/prompts/layer_details_generation.yaml` |
| **Unified summary (Quick Summary)** | Headline + narrative for SummaryPanel; LLM vs fallback | `core/report_view_model.py` (build_unified_consumer_summary), `llm/prompts/summary_generation.yaml` |
| **Executive summary / impact / privacy** | First-pass LLM outputs in the workflow | `core/summary_generator.py`, `core/impact_analyzer.py`, `core/privacy_compliance_analyzer.py` |
| **LLM client & prompts** | Provider chain, timeout, retries; prompt content and variables | `llm/clients/fallback.py`, `llm/clients/__init__.py`, `llm/prompts/*.yaml` |
| **API & DB** | When report_view_model is built; storage of scoring_v2 and report_view_model | `api/main.py`, `api/payload_helpers.py`, `api/database.py` |
| **Frontend** | Normalization, bands, Layer modal labels, SummaryPanel priority | `frontend/src/utils/normalizeScanResult.ts`, `frontend/src/components/report/LayerModal.jsx`, `SummaryPanel.jsx` |

---

## 8. Summary

- **Pipeline 1 (Layer 0):** SignalPackBuilder + adapters normalize analyzer output into SignalPack (single input to scoring).
- **Pipeline 2 (Layer 1):** ScoringEngine computes Security/Privacy/Governance from SignalPack using weights and normalizers, applies gates and coverage cap, and outputs ScoringResult → `scoring_v2`.
- **Pipeline 3:** Legacy rules/report run in governance_node; **report_view_model** is built in the API and includes **Layer Details LLM** (or LayerHumanizer fallback) and **Unified Summary LLM** (or deterministic fallback). Other LLM calls (executive summary, impact, privacy compliance) run in workflow nodes with their own fallbacks.
- **LLM:** All LLM calls go through `invoke_with_fallback()`; prompts are Jinja2 YAML; failures are caught and replaced by deterministic fallbacks so the UI always has copy and scores.

This document, together with the referenced docs, gives full context for working on any part of the security pipeline and engine.
