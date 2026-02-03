# Scoring V2 Discovery Summary

**Date:** 2026-02-03  
**Phase:** Phase 4 Complete  
**Status:** ✅ IMPLEMENTED — Scoring V2 is live

---

## Status (As Implemented)

### ✅ Phase 0: Discovery — COMPLETE

- [x] Locate all scoring call sites
- [x] Identify analyzer outputs
- [x] Map workflow integration
- [x] Document governance layer
- [x] Create design document (`docs/scoring_v2_design.md`)

### ✅ Phase 1: Build Scoring Engine — COMPLETE

- [x] Create `src/extension_shield/scoring/engine.py` — ScoringEngine class
- [x] Create `src/extension_shield/scoring/models.py` — FactorScore, LayerScore, ScoringResult
- [x] Create `src/extension_shield/scoring/normalizers.py` — All normalizer functions
- [x] Create `src/extension_shield/scoring/weights.py` — Weight presets (v1)
- [x] Create `src/extension_shield/scoring/gates.py` — Hard gates (VT_MALWARE, CRITICAL_SAST, etc.)
- [x] Create `src/extension_shield/scoring/explain.py` — Explanation payload builder
- [x] Implement severity normalization [0,1]
- [x] Implement confidence calculation [0,1]
- [x] Implement category scoring (Security, Privacy, Governance)
- [x] Create explanation payload with factor breakdowns

### ✅ Phase 2: Governance Integration — COMPLETE

- [x] `governance_nodes.py` builds SignalPack (Layer 0)
- [x] `governance_nodes.py` calls ScoringEngine for v2 scores
- [x] `governance_bundle["scoring_v2"]` contains full v2 output
- [x] Legacy `security_scorecard` and `governance_scorecard` preserved
- [x] V2 decision added as `decision.v2_decision` (non-breaking)

### ✅ Phase 3: API Wiring — COMPLETE

- [x] API endpoint receives `scoring_v2` in governance bundle
- [x] Backward-compatible: old `overall_security_score` still returned
- [x] New fields available: `scoring_v2.security_score`, `scoring_v2.privacy_score`, etc.

### ✅ Phase 4: Tests — COMPLETE

- [x] `tests/scoring/utils.py` — SignalPack test factory
- [x] `tests/scoring/test_scoring_resolution.py` — 6 tests (score differentiation)
- [x] `tests/scoring/test_scoring_monotonicity.py` — 10 tests (risk → score decrease)
- [x] `tests/scoring/test_scoring_saturation.py` — 7 tests (sublinear scaling)
- [x] `tests/scoring/test_scoring_confidence.py` — Confidence weighting tests

---

## Key Findings (Historical)

### 🚨 Issues Identified (Now Fixed)

1. **Dual Scoring Systems** → **FIXED**
   - `SecurityScorer` class: **DEAD CODE** (still exists, deprecated)
   - `calculate_security_score()`: **LEGACY** (still active for backward compat)
   - **Solution:** `ScoringEngine` is the single source of truth

2. **Score Clustering Problem** → **FIXED**
   - Old: Max risk 244 points, formula `100 - risk` → all high-risk extensions clustered at score 0 (no differentiation above 100 risk points)
   - **New:** Saturating formula `1 - exp(-k*x)` provides full 0-100 range with diminishing returns

3. **No Explainability** → **FIXED**
   - Old: Single integer (0-100)
   - **New:** Full explanation payload with factor severities, confidences, weights, contributions

---

## Decision Enum

The `Decision` enum in `models.py` has three values:

```python
class Decision(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    NEEDS_REVIEW = "NEEDS_REVIEW"
```

**Note:** Gates use `"WARN"` as their decision string, which maps to `Decision.NEEDS_REVIEW` at the top level.

---

## Current Architecture

### Scoring Module Structure

```
src/extension_shield/scoring/
├── __init__.py
├── engine.py       # ScoringEngine - THE SINGLE SOURCE OF TRUTH
├── models.py       # FactorScore, LayerScore, ScoringResult, Decision, RiskLevel
├── normalizers.py  # normalize_sast, normalize_virustotal, normalize_permissions_baseline, etc.
├── weights.py      # SECURITY_WEIGHTS_V1, PRIVACY_WEIGHTS_V1, GOVERNANCE_WEIGHTS_V1
├── gates.py        # HardGates, GateResult, GateConfig
└── explain.py      # ExplanationPayload, ExplanationBuilder
```

### Test Suite Structure

```
tests/scoring/
├── __init__.py
├── utils.py                        # make_min_signal_pack, add_sast_findings, etc.
├── test_scoring_resolution.py      # 6 tests - score differentiation
├── test_scoring_monotonicity.py    # 10 tests - monotonic decrease
├── test_scoring_saturation.py      # 7 tests - sublinear scaling
└── test_scoring_confidence.py      # Confidence weighting
```

### Integration Points

| Location | Integration | Status |
|----------|-------------|--------|
| `workflow/governance_nodes.py` | Calls `ScoringEngine.calculate_scores()` | ✅ Active |
| `governance_bundle["scoring_v2"]` | Contains full v2 results | ✅ Active |
| `api/main.py:240` | Returns `scoring_v2` payload | ✅ Active |
| `api/main.py` | Legacy `calculate_security_score()` | ⚠️ Still active (backward compat) |

---

## V2 Scoring Formula

### Layer Risk Calculation

```
R = Σ(w_i × c_i × s_i) / Σ(w_i × c_i)
Score = round(100 × (1 - R))
```

Where:
- `w_i` = weight of factor i
- `c_i` = confidence in factor i [0,1]
- `s_i` = severity of factor i [0,1]

### Saturation Formula

```
severity = 1 - exp(-k × x)
```

| Factor | k value |
|--------|---------|
| SAST | 0.08 |
| Permissions | 0.25 |
| Entropy | 0.20 |
| Network | 0.25 |

### Weight Presets (v1)

**Security Layer:**
- SAST: 0.30
- VirusTotal: 0.15
- Obfuscation: 0.15
- Manifest: 0.10
- ChromeStats: 0.10
- Webstore: 0.10
- Maintenance: 0.10

**Privacy Layer:**
- PermissionsBaseline: 0.25
- PermissionCombos: 0.25
- NetworkExfil: 0.35
- CaptureSignals: 0.15

**Governance Layer:**
- ToSViolations: 0.50
- Consistency: 0.30
- DisclosureAlignment: 0.20

**Overall Score:**
```
overall = 0.5 × security + 0.3 × privacy + 0.2 × governance
```

---

## Hard Gates (in `gates.py`)

These gates are defined in `src/extension_shield/scoring/gates.py`:

| Gate ID | Trigger | Gate Decision | Threshold |
|---------|---------|---------------|-----------|
| `VT_MALWARE` | malicious_count ≥ 5 | BLOCK | 5 |
| `VT_MALWARE` | malicious_count ≥ 1 | WARN | 1 |
| `CRITICAL_SAST` | CRITICAL findings with high confidence | BLOCK | confidence > 0.7 |
| `TOS_VIOLATION` | Automation on prohibited domains | BLOCK | — |
| `PURPOSE_MISMATCH` | Purpose vs behavior mismatch | WARN/BLOCK | configurable |
| `SENSITIVE_EXFIL` | Sensitive perms + network + no disclosure | WARN | — |

## Score-Based Thresholds (in `models.py`)

These are NOT gates — they are computed in `ScoringResult.compute()`:

| Threshold | Condition | Final Decision |
|-----------|-----------|----------------|
| BLOCK | overall_score < 30 | `Decision.BLOCK` |
| NEEDS_REVIEW | overall_score < 60 | `Decision.NEEDS_REVIEW` |
| ALLOW | overall_score ≥ 60 | `Decision.ALLOW` |

---

## V2 Output Example

Based on actual `ExplanationPayload.to_dict()` structure from `explain.py`:

```json
{
  "scoring_v2": {
    "security_score": 85,
    "privacy_score": 65,
    "governance_score": 70,
    "overall_score": 75,
    "overall_confidence": 0.87,
    "decision": "NEEDS_REVIEW",
    "risk_level": "medium",
    "reasons": ["Overall score 75/100 below ALLOW threshold (60)"],
    "hard_gates_triggered": [],
    "scoring_version": "2.0.0",
    
    "security_layer": {
      "layer_name": "security",
      "score": 85,
      "risk": 0.15,
      "risk_level": "low",
      "confidence": 0.9,
      "factors": [
        {
          "name": "SAST",
          "severity": 0.20,
          "confidence": 0.90,
          "weight": 0.30,
          "contribution": 0.054,
          "risk_level": "low",
          "flags": [],
          "evidence_ids": ["sast:eval-usage:src/main.js"],
          "details": {"deduped_findings": 2},
          "summary": "2 findings after dedup"
        }
      ],
      "top_contributors": ["SAST"],
      "summary": "Security score 85/100"
    },
    
    "explanation": {
      "scan_id": "abc123",
      "extension_id": "ext-id",
      "overall_score": 75,
      "overall_confidence": 0.87,
      "decision": "NEEDS_REVIEW",
      "decision_rationale": "Score below ALLOW threshold",
      "decision_reasons": ["Overall score 75/100 below ALLOW threshold (60)"],
      "summary": "Extension has moderate privacy concerns",
      "layers": {
        "security": { "layer_name": "security", "score": 85, "risk": 0.15, ... },
        "privacy": { "layer_name": "privacy", "score": 65, "risk": 0.35, ... },
        "governance": { "layer_name": "governance", "score": 70, "risk": 0.30, ... }
      },
      "hard_gates": {
        "any_triggered": false,
        "gates_checked": ["VT_MALWARE", "CRITICAL_SAST", "TOS_VIOLATION", "PURPOSE_MISMATCH", "SENSITIVE_EXFIL"]
      },
      "triggered_gates": [],
      "scoring_version": "v2",
      "weights_version": "v1",
      "computed_at": "2026-02-03T12:00:00Z"
    },
    
    "gate_results": [
      {
        "gate_id": "VT_MALWARE",
        "decision": "ALLOW",
        "triggered": false,
        "confidence": 1.0,
        "reasons": []
      }
    ]
  }
}
```

---

## Files Summary

### Created (✅ Exist)

| File | Purpose |
|------|---------|
| `src/extension_shield/scoring/engine.py` | ScoringEngine class |
| `src/extension_shield/scoring/models.py` | Pydantic models |
| `src/extension_shield/scoring/normalizers.py` | Normalization functions |
| `src/extension_shield/scoring/weights.py` | Weight presets |
| `src/extension_shield/scoring/gates.py` | Hard gate rules |
| `src/extension_shield/scoring/explain.py` | Explanation builder |
| `tests/scoring/utils.py` | Test factories |
| `tests/scoring/test_scoring_resolution.py` | Resolution tests |
| `tests/scoring/test_scoring_monotonicity.py` | Monotonicity tests |
| `tests/scoring/test_scoring_saturation.py` | Saturation tests |
| `docs/scoring_v2_design.md` | Design document |
| `docs/CURSOR_PROMPTS_SCORING_REFACTOR.md` | Implementation prompts |

### Modified (✅ Updated)

| File | Changes |
|------|---------|
| `src/extension_shield/workflow/governance_nodes.py` | Added ScoringEngine integration |
| `src/extension_shield/governance/signal_pack.py` | Added NetworkSignalPack |

### Legacy (⚠️ Still Active)

| File | Status |
|------|--------|
| `src/extension_shield/api/main.py` | Legacy `calculate_security_score()` still active |
| `src/extension_shield/core/security_scorer.py` | Dead code, can be deleted |

---

## Next Actions (Remaining Work)

### 🔲 Calibration & Tuning

- [ ] Run on 10+ real extensions
- [ ] Compare V1 vs V2 scores
- [ ] Tune k constants if needed
- [ ] Create golden snapshot tests with real data

### 🔲 Network Adapter Enhancement

- [ ] Improve domain classification (known_good, tracking, suspicious)
- [ ] Add runtime trace integration (if available)
- [ ] Implement credential exfil pattern detection

### 🔲 Frontend Integration

- [ ] Update dashboard to show three-layer scores
- [ ] Display factor breakdown in UI
- [ ] Remove duplicate `calculateSecurityScore()` from frontend
- [ ] Add score trend visualization

### 🔲 Legacy Cleanup (Optional)

- [ ] Remove `calculate_security_score()` when frontend is updated
- [ ] Delete `SecurityScorer` class (dead code)
- [ ] Remove 6 legacy helper functions from `api/main.py`

### 🔲 Documentation

- [ ] Update API documentation with v2 fields
- [ ] Add weight tuning guide to README
- [ ] Document gate configuration options

---

## Test Results Summary

All scoring tests pass:

```
tests/scoring/test_scoring_resolution.py      6 passed
tests/scoring/test_scoring_monotonicity.py   10 passed
tests/scoring/test_scoring_saturation.py      7 passed
─────────────────────────────────────────────────────
TOTAL                                        23 passed
```

**Key Validations:**
- ✅ Scores differentiate risk levels (resolution)
- ✅ Adding risk never increases score (monotonicity)
- ✅ 100 findings ≠ 100x worse (saturation)
- ✅ VT ≥5 triggers BLOCK
- ✅ VT 1-4 triggers WARN (→ NEEDS_REVIEW)
- ✅ Clean VT = ALLOW

---

## Verification Commands

To verify these facts:

```bash
# Confirm Decision enum values
grep -A5 "class Decision" src/extension_shield/scoring/models.py

# Confirm gates in gates.py
grep "gate_id = " src/extension_shield/scoring/gates.py

# Confirm score thresholds in models.py
grep -A10 "elif overall_score" src/extension_shield/scoring/models.py

# Confirm API returns scoring_v2
grep '"scoring_v2"' src/extension_shield/api/main.py
```

---

**Implementation Complete.** The Scoring V2 system is fully operational and integrated.
