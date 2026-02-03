# ExtensionShield Scoring V2 Design Document

**Date:** 2026-02-03  
**Phase:** Phase 0 - Discovery & Planning  
**Goal:** Fair, explainable, and consistent scoring architecture  

---

## 🚨 UPDATED FINDING: Architecture Already Exists!

After deep analysis of the governance module, I discovered that **MOST of the 3-layer architecture already exists**! The problem is simply that the **API doesn't use it**.

### What Already Exists ✅

| Component | File | Lines | Status |
|-----------|------|-------|--------|
| **Layer 0: SignalPack** | `governance/signal_pack.py` | 456 | ✅ Complete with SAST, VT, Entropy, Perms, ChromeStats, Webstore signals |
| **Layer 0: Tool Adapters** | `governance/tool_adapters.py` | 932 | ✅ Complete normalization from raw analyzers |
| **Layer 0: SignalPackBuilder** | `governance/tool_adapters.py:845` | 87 | ✅ Builds complete SignalPack from workflow state |
| **Layer 1: FactorResult** | `governance/scorecard.py:42` | 32 | ✅ Has points, max_points, confidence, details, evidence_ids |
| **Layer 1: SecurityScorecard** | `governance/scorecard.py:76` | 64 | ✅ Has security_score, risk_level, factors dict |
| **Layer 1: 7 Factor Classes** | `governance/scorecard.py:147-1216` | 1070 | ✅ SAST, VT, Entropy, Manifest, Network, Webstore, ChromeStats |
| **Layer 1: ScorecardBuilder** | `governance/scorecard.py:1416` | 84 | ✅ Orchestrates all factor evaluations |
| **Layer 1.5: GovernanceScorecard** | `governance/scorecard.py:1224` | 168 | ✅ Hard gates, ALLOW/BLOCK/NEEDS_REVIEW |
| **Layer 2: Rules Engine** | `governance/rules_engine.py` | 500+ | ✅ Policy rule evaluation |
| **Layer 2: Report Generator** | `governance/report_generator.py` | 200+ | ✅ Final verdict aggregation |
| **Integration: governance_node** | `workflow/governance_nodes.py:49` | 280 | ✅ Runs entire pipeline, stores in governance_bundle |

### What Doesn't Use It ❌

| Component | File | Lines | Problem |
|-----------|------|-------|---------|
| **API calculate_security_score()** | `api/main.py:432-706` | 275 | Uses OLD point-based system, ignores governance layer |
| **SecurityScorer class** | `core/security_scorer.py` | 498 | **DEAD CODE** - never imported or called |
| **Frontend realScanService** | `frontend/.../realScanService.js:195` | 23 | Client-side duplicate logic |

### The Real Refactor (Much Simpler!)

Instead of building from scratch, we need to:
1. **Wire API to use existing** `governance_bundle.security_scorecard.security_score`
2. **Add Privacy layer factors** to existing scorecard architecture
3. **Add normalized [0,1] severity** model to factors (currently uses points)
4. **Remove dead code** (`calculate_security_score`, `SecurityScorer`)
5. **Add confidence-weighted formula** to replace simple point summation

---

## Executive Summary

### Critical Finding: Dual Scoring Systems

The codebase currently has **TWO DIFFERENT SCORING IMPLEMENTATIONS** that produce inconsistent results:

1. **`SecurityScorer` class** (`src/extension_shield/core/security_scorer.py`)
   - Max risk: 211 points (60+30+50+30+28+5+5+3)
   - Used: **NOWHERE** (dead code)
   - Status: ❌ Not used in production workflow

2. **`calculate_security_score()` function** (`src/extension_shield/api/main.py`)
   - Max risk: 244 points (40+30+20+10+1+15+50+30+28+20)
   - Used: Line 186 in `run_analysis_workflow()` → API endpoint `/api/scan/results/{extension_id}`
   - Status: ✅ **ACTIVE** (production system)

### Collapsing Score Problem

**Current Formula:** `score = max(0, min(100, 100 - total_risk_points))`

**Issue:** Maximum risk = 244 points, but score collapses at 100 points.
- Any extension with >100 risk points → **score = 0**
- Scores collapse: 101 pts = 0, 150 pts = 0, 244 pts = 0 (no granularity)
- Real range is NOT 0-100; effective range is **0-100** but **144 points are wasted**

### Architecture Goals (NON-NEGOTIABLE)

1. **Single Source of Truth**: ONE scoring engine used everywhere (API, CLI, MCP, governance)
2. **Normalized Scoring**: Signals → severities [0,1] → confidences [0,1] → weighted risk → score [0-100]
3. **Three Separate Scores**:
   - **SecurityScore** (0-100): Technical vulnerabilities (SAST, VT, entropy)
   - **PrivacyScore** (0-100): Data collection & permissions
   - **GovernanceScore** (0-100): Policy compliance (webstore, manifest, behavior)
4. **Hard Gates**: Governance layer can BLOCK regardless of score (e.g., VirusTotal malware = instant BLOCK)
5. **Explainability**: Return factor severities, confidences, weights, and contributions

---

## Current State Analysis

### Analyzer Outputs (Raw Data Sources)

Located in: `src/extension_shield/core/analyzers/`

| Analyzer | Output Key | Raw Data Structure | Status |
|----------|-----------|-------------------|--------|
| **JavaScriptAnalyzer** | `javascript_analysis` | `{sast_findings: {file: [{check_id, severity, message, extra}]}}` | ✅ |
| **PermissionsAnalyzer** | `permissions_analysis` | `{permissions_details: {perm: {is_reasonable, risk_level, justification}}, screenshot_capture_analysis: {...}}` | ✅ |
| **VirusTotalAnalyzer** | `virustotal_analysis` | `{enabled, files_analyzed, total_malicious, total_suspicious, file_results: [...]}` | ✅ |
| **EntropyAnalyzer** | `entropy_analysis` | `{obfuscated_files, suspicious_files, file_results: [...]}` | ✅ |
| **ChromeStatsAnalyzer** | `chromestats_analysis` | `{enabled, total_risk_score, risk_indicators: [...], install_trends, rating_patterns}` | ✅ |
| **WebstoreAnalyzer** | `webstore_analysis` | `{webstore_analysis: "text summary"}` (LLM-based) | ✅ |
| **ManifestParser** | `manifest_data` | `{name, version, permissions, content_security_policy, ...}` | ✅ |
| **ExtensionMetadata** | `extension_metadata` | `{title, user_count, rating, developer_name, privacy_policy}` | ✅ |

### Current Scoring Logic (Active System)

**Location:** `src/extension_shield/api/main.py:432-706`

```python
def calculate_security_score(state: WorkflowState) -> int:
    """
    Components (risk points deducted from 100):
    - SAST Findings: 40 pts max (CRITICAL/HIGH=8, ERROR/MEDIUM=4, WARNING=1)
    - Permissions Risk: 30 pts max (unreasonable perms, high-risk perms, <all_urls>)
    - Webstore Trust: 20 pts max (rating, user count)
    - Manifest Quality: 10 pts max (missing CSP, MV2 deprecation)
    - Third-Party API Calls: 1 pt (binary detection)
    - Screenshot Capture: 15 pts max (context-aware: tool vs. covert)
    - VirusTotal: 50 pts max (consensus-based: ≥10 malicious=50, ≥5=40, ≥2=30)
    - Entropy/Obfuscation: 30 pts max (adjusted by popularity)
    - ChromeStats Behavioral: 28 pts max (direct from analyzer)
    - Permission-Purpose Alignment: 20 pts max (transparency × covert behavior)
    
    TOTAL: 244 points max
    
    Formula: security_score = max(0, min(100, 100 - final_score))
    """
```

**Helper Functions:**
- `count_total_findings(state)` → int (counts SAST + unreasonable perms)
- `calculate_risk_distribution(state)` → {high, medium, low}
- `determine_overall_risk(state)` → "high" | "medium" | "low"
- `calculate_total_risk_score(state)` → int (legacy severity sum)
- `_calculate_permission_alignment_penalty()` → 0-20 pts (context-aware Vimium vs Honey logic)

### Workflow Integration Points

**File:** `src/extension_shield/workflow/graph.py`

```
START → extension_path_routing_node
     ↓
     extension_metadata_node (fetches webstore data)
     ↓
     chromestats_downloader_node (downloads chromestats JSON)
     ↓
     extension_downloader_node (downloads .crx)
     ↓
     manifest_parser_node (parses manifest.json)
     ↓
     extension_analyzer_node (runs all analyzers → produces analysis_results)
     ↓
     summary_generation_node (creates executive_summary)
     ↓
     governance_node (Layer 1 scoring + policy evaluation)
     ↓
     cleanup_node
     ↓
END
```

**Scoring Call Site:**
- `api/main.py:186`: `calculate_security_score(final_state)` → stores in scan result

### Call Sites (Complete Inventory)

1. **API Endpoint (Production)**
   - File: `src/extension_shield/api/main.py:186`
   - Function: `run_analysis_workflow()`
   - Usage: `scan_results[extension_id]['overall_security_score'] = calculate_security_score(final_state)`

2. **Frontend Service**
   - File: `frontend/src/services/realScanService.js:195`
   - Function: `calculateSecurityScore(analysis)`
   - Status: Client-side recalculation (should use API score)

3. **Governance Layer (Separate System)**
   - File: `src/extension_shield/governance/scorecard.py:1224`
   - Class: `GovernanceScorecard`
   - Status: Uses own scoring (see below)

4. **Dead Code (Not Used)**
   - File: `src/extension_shield/core/security_scorer.py:49`
   - Class: `SecurityScorer.calculate_score()`
   - Status: ❌ Never called

### Governance Layer Scoring (Separate System)

**File:** `src/extension_shield/governance/scorecard.py`

The governance layer has its **own separate scoring implementation** with factors:
- `F_SAST_SEMGREP`: SAST findings (with test exclusion, deduping)
- `F_VIRUSTOTAL_CONSENSUS`: Ratio-based VT scoring
- `F_ENTROPY_OBFUSCATION`: Separate minified vs obfuscated
- `F_MANIFEST_SECURITY`: Manifest security issues
- `F_NETWORK_BEHAVIOR_LITE`: Network endpoint reputation
- `F_WEBSTORE_REPUTATION_BEHAVIOR`: Webstore stats + reviews

**Decision Logic (Hard Gates):**
```python
BLOCK_THRESHOLD = 30     # Security score < 30 → BLOCK
WARN_THRESHOLD = 60      # Security score < 60 → NEEDS_REVIEW
BLOCK_CONFIDENCE_THRESHOLD = 0.7  # Min confidence for BLOCK

# Hard gates (bypass score):
- ANY VirusTotal malware detection → instant BLOCK
- Critical SAST (confidence > 0.7) → instant BLOCK
```

**Output:**
```python
{
  "verdict": "ALLOW" | "NEEDS_REVIEW" | "BLOCK",
  "security_score": 0-100,
  "blocking_factors": ["F_VIRUSTOTAL_CONSENSUS", ...],
  "warning_factors": ["F_WEBSTORE_REPUTATION_BEHAVIOR", ...],
  "verdict_reasons": ["VT: 10 malware detections (score=100%, confidence=95%)", ...],
  "confidence": 0.0-1.0
}
```

---

## Proposed V2 Architecture

### Layer 0: Signal Extraction (Already Exists)

**File:** `src/extension_shield/governance/signal_pack.py`

Normalizes raw analyzer outputs into typed signals:
- `SastFindingNormalized`: {severity, confidence, check_id, ...}
- `PermissionSignal`: {permission, risk_level, is_reasonable, ...}
- `VirusTotalSignal`: {total_malicious, total_suspicious, ...}
- `EntropySignal`: {file, entropy, is_obfuscated, ...}
- `ChromeStatsSignal`: {risk_indicators, trust_score, ...}
- `WebstoreStatsSignal`: {rating, user_count, ...}

**Status:** ✅ Already implemented (used by governance layer)

### Layer 1: Normalized Scoring (NEW)

**File:** `src/extension_shield/core/scoring_engine.py` (NEW)

```python
class ScoringEngine:
    """
    Unified scoring engine that produces three separate scores.
    
    Architecture:
    1. Signal → Severity [0,1]: Map raw values to normalized severity
    2. Confidence [0,1]: How certain are we about this signal?
    3. Weighted Risk: severity × confidence × category_weight
    4. Score [0-100]: Aggregate weighted risks
    """
    
    def calculate_scores(self, signal_pack: SignalPack) -> ScoringResult:
        """
        Returns:
            ScoringResult(
                security_score=0-100,       # Technical vulnerabilities
                privacy_score=0-100,        # Data collection & permissions
                governance_score=0-100,     # Policy compliance
                overall_score=0-100,        # Weighted average
                explanation=ExplanationPayload(
                    factors=[
                        {
                            "name": "SAST_CRITICAL",
                            "severity": 0.95,       # [0,1]
                            "confidence": 0.90,     # [0,1]
                            "weight": 0.30,         # % of category
                            "contribution": 25.65   # Impact on score
                        },
                        ...
                    ],
                    category_weights={
                        "security": 0.50,
                        "privacy": 0.30,
                        "governance": 0.20
                    }
                )
            )
        """
```

**Severity Normalization (Examples):**

| Signal | Raw Value | Normalized Severity [0,1] | Logic |
|--------|-----------|--------------------------|-------|
| SAST CRITICAL | count | `min(1.0, count / 5)` | 5+ criticals = max severity |
| VirusTotal | malicious_count | `min(1.0, count / 10)` | 10+ engines = max severity |
| Entropy | entropy_value | `(entropy - 4.0) / 4.0` | 4.0=normal, 8.0=max |
| Permissions | unreasonable_count | `min(1.0, count / 10)` | 10+ unreasonable = max |
| User Count | users | `1.0 - log10(users) / 7` | <100=1.0, >10M=0.0 |

**Confidence Calculation:**

| Signal | Confidence | Logic |
|--------|-----------|-------|
| SAST | `0.9` if in production code, `0.6` if in test/lib | Test exclusion awareness |
| VirusTotal | `min(1.0, detections / total_engines)` | Consensus-based |
| Permissions (LLM) | `0.7` | LLM analysis = medium confidence |
| Entropy | `0.8` if high-risk patterns, `0.5` otherwise | Pattern-based |
| ChromeStats | `0.6` | Behavioral signals = noisy |

### Layer 2: Category Scoring (NEW)

**Three Separate Scores:**

1. **SecurityScore (0-100)**: Technical vulnerabilities
   - SAST findings (40% weight)
   - VirusTotal detections (30%)
   - Entropy/obfuscation (20%)
   - Manifest security (10%)

2. **PrivacyScore (0-100)**: Data collection risks
   - Permissions reasonableness (50%)
   - Screenshot/clipboard capture (20%)
   - Third-party API calls (15%)
   - Permission-purpose alignment (15%)

3. **GovernanceScore (0-100)**: Policy compliance
   - Webstore reputation (40%)
   - ChromeStats behavioral (30%)
   - Manifest quality (20%)
   - Network domains (10%)

**Overall Score:**
```
OverallScore = (SecurityScore × 0.5) + (PrivacyScore × 0.3) + (GovernanceScore × 0.2)
```

### Layer 3: Governance Decision (Already Exists)

**File:** `src/extension_shield/governance/report_generator.py`

**Hard Gates (Bypass Score):**
```python
# Instant BLOCK (high-confidence signals)
if virustotal.malicious > 0:
    return "BLOCK"

if any(sast.severity == "CRITICAL" and sast.confidence > 0.7):
    return "BLOCK"

# Score-based decisions
if security_score < 30:
    return "BLOCK"
elif security_score < 60 or privacy_score < 50:
    return "NEEDS_REVIEW"
else:
    return "ALLOW"
```

**Decision Output:**
```python
{
  "verdict": "ALLOW" | "NEEDS_REVIEW" | "BLOCK",
  "security_score": 85,
  "privacy_score": 60,
  "governance_score": 75,
  "overall_score": 74,
  "blocking_reasons": [
    "VirusTotal: 5 malware detections (confidence=95%)"
  ],
  "warning_reasons": [
    "Privacy: Screenshot capture without disclosure (severity=80%, confidence=70%)"
  ]
}
```

---

## Signal-to-Factor Mapping

### SAST Findings → SecurityScore

**Raw Data:**
```json
{
  "javascript_analysis": {
    "sast_findings": {
      "background.js": [
        {
          "check_id": "javascript.crypto.insecure-random",
          "severity": "ERROR",
          "message": "Insecure random number generation",
          "extra": {
            "severity": "ERROR",
            "metadata": {...}
          }
        }
      ]
    }
  }
}
```

**Normalized Signal:**
```python
SastFindingNormalized(
    check_id="javascript.crypto.insecure-random",
    severity=0.75,        # ERROR → 0.75 (CRITICAL=1.0, HIGH=0.9, ERROR=0.75, WARNING=0.5, INFO=0.1)
    confidence=0.9,       # High confidence (production code)
    file_path="background.js",
    is_test_file=False,
    is_library=False
)
```

**Scoring:**
```python
# SAST contributes 40% to SecurityScore
weight = 0.40

# Severity aggregation (max of criticals, or count-based)
severities = [f.severity for f in sast_findings]
max_severity = max(severities) if severities else 0.0

# Apply confidence
effective_severity = max_severity * average_confidence

# Impact on SecurityScore
risk_contribution = effective_severity * weight  # 0.75 × 0.9 × 0.40 = 0.27 (27 points)
```

### VirusTotal → SecurityScore

**Raw Data:**
```json
{
  "virustotal_analysis": {
    "total_malicious": 5,
    "total_suspicious": 2,
    "files_analyzed": 3,
    "file_results": [
      {
        "virustotal": {
          "detection_stats": {
            "malicious": 5,
            "total_engines": 76
          }
        }
      }
    ]
  }
}
```

**Normalized Signal:**
```python
severity = min(1.0, total_malicious / 10)  # 5 malicious → 0.5 severity
confidence = total_malicious / total_engines  # 5/76 = 0.066 (low consensus)

# BUT: ANY malware = hard gate BLOCK
if total_malicious > 0:
    return "BLOCK"  # Bypass scoring
```

### Permissions → PrivacyScore

**Raw Data:**
```json
{
  "permissions_analysis": {
    "permissions_details": {
      "cookies": {
        "is_reasonable": false,
        "risk_level": "high",
        "justification_reasoning": "Not justified for stated purpose"
      }
    },
    "screenshot_capture_analysis": {
      "detected": true,
      "risk_score": 10
    }
  }
}
```

**Normalized Signals:**
```python
PermissionSignal(
    permission="cookies",
    severity=0.8,         # high risk + unreasonable → 0.8
    confidence=0.7,       # LLM analysis = medium confidence
    is_reasonable=False
)

ScreenshotSignal(
    detected=True,
    severity=0.6,         # Context-aware: covert=1.0, disclosed=0.3
    confidence=0.9,       # High confidence (static analysis)
)
```

### ChromeStats → GovernanceScore

**Raw Data:**
```json
{
  "chromestats_analysis": {
    "total_risk_score": 15,
    "risk_indicators": [
      "High uninstall rate",
      "Sudden rating drop"
    ],
    "install_trends": {
      "uninstall_rate": 0.35
    }
  }
}
```

**Normalized Signal:**
```python
severity = chromestats.total_risk_score / 28  # 15/28 = 0.54
confidence = 0.6  # Behavioral signals = noisy

# Contributes 30% to GovernanceScore
risk_contribution = 0.54 × 0.6 × 0.30 = 0.097 (9.7 points)
```

---

## Implementation Plan (Phase 1+)

### Phase 1: Create Unified Scoring Engine

**Tasks:**
1. Create `src/extension_shield/core/scoring_engine.py`
2. Implement `ScoringEngine` class with:
   - `normalize_severity()`: Raw value → [0,1]
   - `calculate_confidence()`: Signal-specific logic
   - `calculate_category_score()`: Weighted aggregation
   - `calculate_scores()`: Main entry point
3. Create `ScoringResult` dataclass with explanation payload
4. Add comprehensive unit tests

**Deliverables:**
- New scoring engine (independent of current system)
- Test coverage >90%
- No behavior change (parallel implementation)

### Phase 2: Migrate Call Sites

**Tasks:**
1. Update `api/main.py:186`:
   ```python
   # OLD
   overall_security_score = calculate_security_score(final_state)
   
   # NEW
   from extension_shield.core.scoring_engine import ScoringEngine
   engine = ScoringEngine()
   signal_pack = SignalPack.from_analysis_results(final_state)
   scores = engine.calculate_scores(signal_pack)
   
   scan_results[extension_id].update({
       "overall_security_score": scores.overall_score,
       "security_score": scores.security_score,
       "privacy_score": scores.privacy_score,
       "governance_score": scores.governance_score,
       "scoring_explanation": scores.explanation.to_dict()
   })
   ```

2. Update governance layer to use unified scores
3. Update frontend to display three separate scores
4. Add API endpoint: `/api/scan/scoring_breakdown/{extension_id}`

**Deliverables:**
- All call sites migrated
- API returns three scores + explanation
- Frontend displays detailed breakdown

### Phase 3: Remove Legacy Code

**Tasks:**
1. Delete `SecurityScorer` class (dead code)
2. Delete `calculate_security_score()` from `api/main.py`
3. Delete helper functions:
   - `count_total_findings()`
   - `calculate_risk_distribution()`
   - `determine_overall_risk()`
   - `calculate_total_risk_score()`
   - `_calculate_permission_alignment_penalty()`
4. Update governance layer to use hard gates

**Deliverables:**
- Single source of truth
- No duplicate scoring logic
- Clean codebase

### Phase 4: Validation & Calibration

**Tasks:**
1. Run on existing test set (10 extensions in `extensions_storage/`)
2. Compare V1 vs V2 scores
3. Adjust weights/thresholds based on ground truth
4. Document calibration decisions

**Deliverables:**
- Validated weights
- Documented calibration process
- Regression tests with golden snapshots

---

## Risk Analysis

### Risks

1. **Breaking Changes**: Existing frontend/integrations expect single `overall_security_score`
   - **Mitigation**: Keep `overall_security_score` as weighted average
   - Add new fields: `security_score`, `privacy_score`, `governance_score`

2. **Score Changes**: New system may produce different scores for same extensions
   - **Mitigation**: Run parallel scoring (V1 + V2) during migration
   - Document score deltas in migration report

3. **Performance**: More complex scoring logic
   - **Mitigation**: Profile and optimize (should be <100ms)

4. **Calibration**: Weights may need tuning
   - **Mitigation**: Use golden test set for validation
   - Iterate based on feedback

### Open Questions

1. **Weight Distribution**: Are 50% security / 30% privacy / 20% governance the right weights?
   - **Decision**: Start with these, calibrate in Phase 4

2. **Confidence Aggregation**: Average? Max? Weighted?
   - **Decision**: Use weighted average (factor_confidence × factor_weight)

3. **Test File Handling**: Exclude test files from SAST scoring?
   - **Decision**: Include but reduce confidence (0.9 → 0.6)

4. **ChromeStats Reliability**: Trust score of 0.6 appropriate?
   - **Decision**: Yes, behavioral signals are noisy (validate in Phase 4)

---

## Appendix: Current Scoring Formula (Full Detail)

### Formula Components (244 Max Points)

```python
# Component 1: SAST (40 pts max)
for finding in sast_findings:
    if severity in ("CRITICAL", "HIGH"):
        sast_score += 8
    elif severity in ("ERROR", "MEDIUM"):
        sast_score += 4
    elif severity == "WARNING":
        sast_score += 1
sast_score = min(40, sast_score)

# Component 2: Permissions (30 pts max)
for perm in permissions_details:
    if not perm.is_reasonable:
        if perm.risk_level == "high":
            permissions_score += 5
        elif perm.risk_level == "medium":
            permissions_score += 2
        else:
            permissions_score += 1
permissions_score = min(30, permissions_score)

# Component 3: Webstore Trust (20 pts max)
if rating < 3.0:
    webstore_score += 10
elif rating < 4.0:
    webstore_score += 5
elif rating < 4.5:
    webstore_score += 2

if user_count < 10000:
    webstore_score += 8
elif user_count < 100000:
    webstore_score += 5
elif user_count < 1000000:
    webstore_score += 2
webstore_score = min(20, webstore_score)

# Component 4: Manifest (10 pts max)
if not manifest.name or manifest.name.startswith("__MSG_"):
    manifest_score += 3
if not manifest.description:
    manifest_score += 2
if not manifest.content_security_policy:
    manifest_score += 2
if not manifest.update_url:
    manifest_score += 1
manifest_score = min(10, manifest_score)

# Component 5: Third-Party APIs (1 pt)
if any("third_party" in finding.check_id for finding in sast_findings):
    third_party_api_score = 1

# Component 6: Screenshot Capture (15 pts max)
if screenshot_analysis.detected:
    if is_screenshot_tool:
        screenshot_score = 1
    else:
        if has_network:
            screenshot_score = 10
        if has_storage and has_network:
            screenshot_score = 15

# Component 7: VirusTotal (50 pts max)
if total_malicious >= 10:
    virustotal_score = 50
elif total_malicious >= 5:
    virustotal_score = 40
elif total_malicious >= 2:
    virustotal_score = 30
elif total_malicious >= 1:
    virustotal_score = 15
elif total_suspicious > 0:
    virustotal_score = min(20, total_suspicious * 5)

# Component 8: Entropy (30 pts max)
if user_count >= 100000:
    popularity_modifier = 0.5
else:
    popularity_modifier = 1.0

base_obfuscation_risk = min(20, obfuscated_files * 8)
entropy_score += int(base_obfuscation_risk * popularity_modifier)
entropy_score += min(10, suspicious_files * 4)
entropy_score = min(30, entropy_score)

# Component 9: ChromeStats (28 pts max)
chromestats_score = min(28, chromestats_analysis.total_risk_score)

# Component 10: Permission-Purpose Alignment (20 pts max)
# Complex context-aware logic (150 lines)
alignment_penalty = _calculate_permission_alignment_penalty(
    manifest, permissions_details, permissions_analysis, analysis_results
)

# Final Score
final_score = (
    sast_score + permissions_score + webstore_score + manifest_score +
    third_party_api_score + screenshot_score + virustotal_score +
    entropy_score + chromestats_score + alignment_penalty
)

security_score = max(0, min(100, 100 - final_score))
```

---

## Appendix: Example Scoring Breakdown

### Example: "Honey" Extension (Malicious)

**Raw Signals:**
```json
{
  "sast_findings": {"background.js": [
    {"severity": "CRITICAL", "check_id": "javascript.xss.dom-based-xss"}
  ]},
  "virustotal": {"total_malicious": 8},
  "permissions": {
    "cookies": {"is_reasonable": false, "risk_level": "high"},
    "history": {"is_reasonable": false, "risk_level": "high"}
  },
  "screenshot_capture": {"detected": true},
  "chromestats": {"uninstall_rate": 0.45}
}
```

**V2 Scores:**
```python
SecurityScore = 15/100  # CRITICAL SAST + VT malware
  - SAST: severity=1.0, confidence=0.9, weight=0.4 → 36 pts risk
  - VirusTotal: severity=0.8, confidence=0.11, weight=0.3 → 24 pts risk
  - Total: 100 - 60 = 40 (capped at 15 due to hard gates)

PrivacyScore = 20/100  # Unreasonable perms + covert screenshot
  - Permissions: severity=0.8, confidence=0.7, weight=0.5 → 28 pts risk
  - Screenshot: severity=1.0, confidence=0.9, weight=0.2 → 18 pts risk
  - Alignment: severity=0.9, confidence=0.8, weight=0.15 → 11 pts risk
  - Total: 100 - 57 = 43 (capped at 20 due to hard gates)

GovernanceScore = 40/100  # High uninstall rate
  - ChromeStats: severity=0.45, confidence=0.6, weight=0.3 → 8 pts risk
  - Total: 100 - 8 = 92 (no hard gates)

OverallScore = 15×0.5 + 20×0.3 + 40×0.2 = 21/100

Verdict: BLOCK (VirusTotal malware + SecurityScore < 30)
```

### Example: "Vimium" Extension (Legitimate)

**Raw Signals:**
```json
{
  "permissions": {
    "<all_urls>": {"is_reasonable": true, "risk_level": "high"}
  },
  "manifest": {"name": "Vimium", "description": "keyboard shortcuts for navigation"},
  "webstore": {"rating": 4.8, "user_count": 2000000}
}
```

**V2 Scores:**
```python
SecurityScore = 95/100  # No vulnerabilities
  - SAST: severity=0.0 → 0 pts risk
  - Total: 100 - 0 = 100 (capped at 95 floor)

PrivacyScore = 80/100  # <all_urls> but justified
  - Permissions: severity=0.3 (justified), confidence=0.7, weight=0.5 → 11 pts risk
  - Alignment: severity=0.1 (transparent), confidence=0.9, weight=0.15 → 1 pt risk
  - Total: 100 - 12 = 88 (capped at 80)

GovernanceScore = 95/100  # High rating + popular
  - Webstore: severity=0.02, confidence=0.9, weight=0.4 → 1 pt risk
  - Total: 100 - 1 = 99 (capped at 95)

OverallScore = 95×0.5 + 80×0.3 + 95×0.2 = 90/100

Verdict: ALLOW (all scores > thresholds)
```

---

## Next Steps

1. **Review & Approve** this design document
2. **Phase 1 Implementation**: Create `ScoringEngine` class
3. **Validation**: Run parallel scoring on test set
4. **Phase 2 Migration**: Update call sites
5. **Phase 3 Cleanup**: Remove legacy code
6. **Phase 4 Calibration**: Validate and tune weights

**Estimated Timeline:** 1-2 weeks for complete implementation

**Success Criteria:**
- ✅ Single source of truth (no duplicate scoring)
- ✅ Three separate scores (Security, Privacy, Governance)
- ✅ Hard gates for high-confidence threats
- ✅ Explainable factor contributions
- ✅ No score collapse (normalized to [0,100])
- ✅ Pass all existing tests + new golden snapshots

