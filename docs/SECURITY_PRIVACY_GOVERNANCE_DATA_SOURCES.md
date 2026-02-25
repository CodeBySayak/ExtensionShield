# Security, Privacy & Governance — Where Each Data and Summary Comes From

This document traces **every piece of data** shown in the scan results UI for Security, Privacy, and Governance — from raw analyzers to the final display. Use it to understand the data lineage for Quick Summary, TOP 3 FINDINGS, layer scores, and each check/factor.

---

## 1. Quick Summary (✨)

The Quick Summary is the main consumer-facing block at the top of the scan results page.

| UI Element | Data Source | How It's Built |
|------------|-------------|----------------|
| **Headline** | `report_view_model.unified_summary.headline` | **LLM:** `build_unified_consumer_summary()` in `core/report_view_model.py` using prompt `consumer_summary_unified` from `llm/prompts/summary_generation.yaml`. Max 100 chars. |
| **Narrative** | `report_view_model.unified_summary.narrative` | **LLM:** Same function. Single flowing text weaving capabilities, concerns, and recommendation. Max 400 chars. |
| **TL;DR / Concerns / Recommendation** | `unified_summary.tldr`, `concerns`, `recommendation` | **LLM** or **fallback:** Used when `narrative` is empty. Fallback: `_fallback_unified_consumer_summary()` builds deterministic text from layer_details key_points or highlights. |
| **Verdict badge** (REVIEW, SAFE, BLOCKED) | `scores.decision` | From `scoring_v2.decision` (ALLOW → SAFE, WARN → REVIEW, BLOCK → BLOCKED). Source: `ScoringEngine.calculate_scores()` in `scoring/engine.py`. |

### Fallback chain (when LLM fails or no unified_summary)

1. **Consumer summary** (`report_view_model.consumer_summary`): Verdict, reasons, access, action — built by `build_consumer_summary()` (deterministic).
2. **Legacy highlights**: `oneLiner` + `keyPoints` from `normalizeHighlights(raw)`.
3. **Engine concerns**: From `keyFindings` (high/medium severity) — built by `buildKeyFindings()` in `normalizeScanResult.ts`.

### LLM inputs for unified summary

- `extension_name`, `score`, `score_label`, `security_score`, `privacy_score`, `governance_score`, `decision`
- `host_access_summary_json`, `permissions_json`, `what_it_can_do_json`
- `key_findings_json`, `security_findings_json`, `privacy_findings_json`, `governance_findings_json`
- Findings come from: `layer_details.key_points` + `scoring_v2` factors with `severity >= 0.3` + `hard_gates_triggered`

---

## 2. TOP 3 FINDINGS (⚡)

| UI Element | Data Source | How It's Built |
|------------|-------------|----------------|
| **Title** | `keyFindings[].title` | From `buildKeyFindings()` in `frontend/src/utils/normalizeScanResult.ts`. |
| **Summary** | `keyFindings[].summary` | Same. Format: `"{Layer} factor: severity X%, confidence Y%"` for factors; `"{Layer} hard gate triggered: {gate}"` for gates. |

### buildKeyFindings() logic (priority order)

1. **Hard gates first** (`scoring_v2.hard_gates_triggered`): Each gate → high-severity finding. Layer from `gateIdToLayer(gate)`.
2. **Top 3 factors by risk contribution** where `severity >= 0.4`: From `security_layer.factors`, `privacy_layer.factors`, `governance_layer.factors`. Sorted by `contribution` (riskContribution) descending, take top 3.
3. **Decision reasons** (if no findings): From `scoring_v2.decision_reasons` or `scoring_v2.reasons`.
4. **Legacy** (if still empty): From `raw.summary.key_findings`.

### topFindings passed to SummaryPanel

- Built in `ScanResultsPageV2.jsx`: `topThreeFindings = [...allSecurityFindings, ...allPrivacyFindings, ...allGovernanceFindings].slice(0, 3)`.
- Each item: `{ title, summary }` from deduped `keyFindings` + `extractFindingsByLayer(scanResults)`.
- Only "actionable" findings are shown (filters out factor-only labels like Maintenance, Webstore, Manifest when summary is just "Contribution: X%").

---

## 3. Security Section (🛡️)

### 3.1 Score & Band

| UI Element | Data Source | Origin |
|------------|-------------|--------|
| **Score (e.g. 84)** | `scoring_v2.security_score` | `ScoringEngine.calculate_scores()` → `ScoringResult.security_score`. Formula: `round(100 × (1 - R))` where R = confidence-weighted risk from security factors. |
| **Band** (Safe / Needs Review / Not Safe) | `scores.security.band` | From `scoring_v2.security_layer.risk_level` or score thresholds: ≥85 = GOOD (Safe), 60–84 = WARN (Needs Review), 0–59 = BAD (Not Safe). Gate results can override (e.g. CRITICAL_SAST → BAD). |
| **One-liner** | `layer_details.security.one_liner` | **LLM:** `LayerDetailsGenerator` or **fallback:** `LayerHumanizer.generate_layer_details_fallback()`. Max 150 chars. |

### 3.2 "X checks run, Y with issues"

| UI Element | Data Source | Origin |
|------------|-------------|--------|
| **Total checks** | `factorsByLayer.security.length` | Count of factors in `scoring_v2.security_layer.factors` (always 7 for Security). |
| **With issues** | Factors where `severity >= 0.4` | Frontend: `humanised.filter(f => f.statusType === 'issues').length`. |

### 3.3 Security checks (grouped by category)

Each row comes from `scoring_v2.security_layer.factors`. The frontend maps factor names to labels via `FACTOR_HUMAN` in `LayerModal.jsx` and groups by `category` using `CATEGORY_LABELS`.

| Factor Name | UI Label | Category | Raw Data Source | Normalizer |
|-------------|----------|----------|-----------------|------------|
| **SAST** | Code Safety | Code Checks | `analysis_results.javascript_analysis.sast_findings` → **SastAdapter** → `signal_pack.sast` | `normalize_sast()` — weighted sum of findings (CRITICAL=15, HIGH=8, etc.), severity = `1 - exp(-0.12 × sum)` |
| **VirusTotal** | Malware Scan | Threat Detection | `analysis_results.virustotal` → **VirusTotalAdapter** → `signal_pack.virustotal` | `normalize_virustotal()` — malicious count → bands (0→0, 1→0.3, 2–4→0.6, 5–9→0.8, ≥10→1.0) |
| **Obfuscation** | Hidden Code | Code Checks | `analysis_results.entropy_analysis` → **EntropyAdapter** → `signal_pack.entropy` | `normalize_obfuscation()` — `2×obfuscated + 1×suspicious` → severity; confidence reduced by popularity |
| **Manifest** | Extension Config | Code Checks | `manifest` (parsed manifest.json) | `normalize_manifest_posture()` — missing CSP +0.3, MV2 +0.2, broad host +0.3 |
| **ChromeStats** | Threat Intelligence | Threat Detection | `analysis_results.chromestats` → **ChromeStatsAdapter** → `signal_pack.chromestats` | Uses precomputed `total_risk_score`; severity = saturating function |
| **Webstore** | Store Reputation | Trust Signals | `metadata` / `analysis_results.webstore_stats` → **WebstoreStatsAdapter** → `signal_pack.webstore_stats` | Low rating, low users, no privacy policy → severity |
| **Maintenance** | Update Freshness | Trust Signals | `metadata.last_updated` / `webstore_stats.last_updated` | Days since update: >365→0.8, 180–365→0.6, 90–180→0.4, <90→0.1 |

### 3.4 Status badge (No Issues / Issues Found)

- **Severity ≥ 0.4** → "Issues Found"
- **Severity < 0.4** → "No Issues"

---

## 4. Privacy Section (🔒)

### 4.1 Score & Band

| UI Element | Data Source | Origin |
|------------|-------------|--------|
| **Score** | `scoring_v2.privacy_score` | `ScoringEngine.calculate_scores()` → confidence-weighted risk from privacy factors. |
| **Band** | Same logic as Security | From `privacy_layer.risk_level` or score thresholds; SENSITIVE_EXFIL gate can override. |
| **One-liner** | `layer_details.privacy.one_liner` | LLM or LayerHumanizer fallback. |

### 4.2 Privacy checks

| Factor Name | UI Label | Category | Raw Data Source | Normalizer |
|-------------|----------|----------|-----------------|------------|
| **PermissionsBaseline** | Permission Risk | What It Can Access | `manifest.permissions` + `permissions_analysis` → **PermissionsAdapter** → `signal_pack.permissions` | `n = high_risk + unreasonable`; severity = `1 - exp(-0.25 × n)` |
| **PermissionCombos** | Dangerous Combos | What It Can Access | Same permissions signal | Checks dangerous combos (cookies+webRequest, clipboardRead+webRequest, debugger, etc.); fixed severity per combo |
| **NetworkExfil** | Data Sharing | Data Handling | `analysis_results` (network/SAST) → **NetworkAdapter** → `signal_pack.network` | Domain risk + suspicious flags (HTTP, base64, dynamic URL, credential patterns) |
| **CaptureSignals** | Screen / Tab Capture | Data Handling | Permissions (desktopCapture, tabCapture) + permissions_analysis | Tab/desktop capture + network access → severity |

---

## 5. Governance Section (📋)

### 5.1 Score & Band

| UI Element | Data Source | Origin |
|------------|-------------|--------|
| **Score** | `scoring_v2.governance_score` | `ScoringEngine.calculate_scores()` → `_compute_governance_factors()`. |
| **Band** | Same logic | TOS_VIOLATION, PURPOSE_MISMATCH gates can override. |
| **One-liner** | `layer_details.governance.one_liner` | LLM or LayerHumanizer fallback. |

### 5.2 Governance checks

| Factor Name | UI Label | Category | Raw Data Source | Normalizer |
|-------------|----------|----------|-----------------|------------|
| **ToSViolations** | Policy Violations | Rules & Policies | Computed in engine from: prohibited perms (debugger, proxy, nativeMessaging), broad host + VT, travel-docs risk | +0.5 per prohibited perm; +0.4 for broad host + VT; travel-docs risk up to 0.9 |
| **Consistency** | Behavior Match | Rules & Policies | Extension description/claims vs security+privacy risk | Benign claim + high risk → 0.6; "offline" + broad host → 0.4 |
| **DisclosureAlignment** | Disclosure Accuracy | Rules & Policies | `webstore_stats.has_privacy_policy` + network/data collection signals | No policy + data collection → 0.5; no policy + network → 0.3 |

---

## 6. End-to-End Data Flow

```
Extension (CRX / CWS URL / ID)
    ↓
Workflow: extension_analyzer_node
    → analysis_results (SAST, VirusTotal, entropy, permissions, chromestats, network, webstore)
    → metadata (CWS / chrome-stats)
    → manifest (parsed manifest.json)
    ↓
governance_node:
    Pipeline 1: SignalPackBuilder.build(analysis_results, metadata, manifest)
        → SastAdapter, VirusTotalAdapter, EntropyAdapter, WebstoreStatsAdapter,
          PermissionsAdapter, ChromeStatsAdapter, NetworkAdapter
        → SignalPack (sast, virustotal, entropy, webstore_stats, permissions, chromestats, network)
    Pipeline 2: ScoringEngine.calculate_scores(signal_pack, manifest, user_count)
        → normalizers.py: severity + confidence per factor
        → weights.py: factor weights
        → gates.py: hard gates (VT_MALWARE, CRITICAL_SAST, TOS_VIOLATION, etc.)
        → ScoringResult (security_layer, privacy_layer, governance_layer, decision)
    ↓
API: build_report_view_model_safe()
    → LayerDetailsGenerator (LLM) or LayerHumanizer (fallback) → layer_details
    → build_unified_consumer_summary() (LLM) or _fallback_unified_consumer_summary() → unified_summary
    → build_consumer_summary() → consumer_summary
    ↓
Response: scoring_v2 + report_view_model
    ↓
Frontend: normalizeScanResult(raw)
    → scores, factorsByLayer, keyFindings, permissions
    ↓
ScanResultsPageV2 → SummaryPanel (Quick Summary, TOP 3 FINDINGS)
                → LayerModal (per layer: score, band, one-liner, checks)
```

---

## 7. Key Files Reference

| Purpose | File |
|---------|------|
| Signal extraction (raw → SignalPack) | `governance/tool_adapters.py`, `governance/signal_pack.py` |
| Severity/confidence per factor | `scoring/normalizers.py` |
| Layer scores, decision, gates | `scoring/engine.py`, `scoring/gates.py`, `scoring/weights.py` |
| Report view model, unified summary | `core/report_view_model.py` |
| Layer details (one-liner, key_points) | `core/layer_details_generator.py`, `scoring/humanize.py` |
| Frontend normalization | `frontend/src/utils/normalizeScanResult.ts` |
| Layer modal (factors, labels, categories) | `frontend/src/components/report/LayerModal.jsx` |
| Quick Summary, TOP 3 FINDINGS | `frontend/src/components/report/SummaryPanel.jsx` |

---

## 8. Example: "Authenticator" Quick Summary

For the sample you provided:

- **"Review before installing — Authenticator needs some attention"** → From `unified_summary.headline` (LLM).
- **"Some permissions and behaviors need review..."** → From `unified_summary.narrative` (LLM).
- **"Maintenance: moderate risk"** → From `Maintenance` factor (Update Freshness) — severity from days since last update.
- **"PermissionsBaseline: low risk"** → From `PermissionsBaseline` factor (Permission Risk).
- **"Data access: can access current tab information"** → From `what_it_can_do` / permissions (e.g. `activeTab` → "can access the page you're on").
- **"View risky permissions" / "View network domains"** → Action buttons; handlers from `ScanResultsPageV2`.

**TOP 3 FINDINGS:**
- **Security factor: severity 80%, confidence 90%** → Top factor by risk contribution from `security_layer.factors` (e.g. Maintenance).
- **Privacy factor: severity 53%, confidence 100%** → Top factor from `privacy_layer.factors` (e.g. PermissionsBaseline).

**Layer scores (84, 79, 100):** From `scoring_v2.security_score`, `privacy_score`, `governance_score`.

**"7 checks run, 1 with issues" (Security):** 7 factors total; 1 has severity ≥ 0.4.

---

*Last updated to reflect ExtensionShield security pipeline v2.0.0.*
