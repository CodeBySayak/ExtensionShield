"""
ExtensionShield Scoring Module (V2)

Provides normalized, explainable, and consistent scoring architecture with:
- Three separate layer scores: Security, Privacy, Governance
- Normalized [0,1] severities and confidences
- Versioned, configurable weight presets
- Full explainability with factor contributions and evidence

Usage:
    from extension_shield.scoring import (
        FactorScore,
        LayerScore,
        ScoringResult,
        SECURITY_WEIGHTS_V1,
        PRIVACY_WEIGHTS_V1,
        GOVERNANCE_WEIGHTS_V1,
        LAYER_WEIGHTS,
        normalize_security_factors,
        normalize_privacy_factors,
    )
"""

from extension_shield.scoring.models import (
    FactorScore,
    LayerScore,
    ScoringResult,
    RiskLevel,
    Decision,
)

from extension_shield.scoring.weights import (
    SECURITY_WEIGHTS_V1,
    PRIVACY_WEIGHTS_V1,
    GOVERNANCE_WEIGHTS_V1,
    LAYER_WEIGHTS,
    WeightPreset,
    get_weight_preset,
    SecurityFactors,
    PrivacyFactors,
    GovernanceFactors,
)

from extension_shield.scoring.normalizers import (
    # Security normalizers
    normalize_sast,
    normalize_virustotal,
    normalize_entropy,
    normalize_manifest_posture,
    normalize_chromestats,
    normalize_webstore_trust,
    normalize_maintenance_health,
    # Privacy normalizers
    normalize_permissions_baseline,
    normalize_permission_combos,
    normalize_network_exfil,
    normalize_capture_signals,
    # Batch normalizers
    normalize_security_factors,
    normalize_privacy_factors,
)

from extension_shield.scoring.gates import (
    GateResult,
    GateConfig,
    HardGates,
    evaluate_hard_gates,
    get_hard_gate_summary,
)

from extension_shield.scoring.engine import (
    ScoringEngine,
    calculate_extension_score,
    get_score_explanation,
)

from extension_shield.scoring.explain import (
    ExplanationBuilder,
    ExplanationPayload,
    FactorExplanation,
    LayerExplanation,
    build_explanation,
    get_ui_explanation,
)

__all__ = [
    # Models
    "FactorScore",
    "LayerScore",
    "ScoringResult",
    "RiskLevel",
    "Decision",
    # Weights
    "SECURITY_WEIGHTS_V1",
    "PRIVACY_WEIGHTS_V1",
    "GOVERNANCE_WEIGHTS_V1",
    "LAYER_WEIGHTS",
    "WeightPreset",
    "get_weight_preset",
    # Factor name constants
    "SecurityFactors",
    "PrivacyFactors",
    "GovernanceFactors",
    # Security normalizers
    "normalize_sast",
    "normalize_virustotal",
    "normalize_entropy",
    "normalize_manifest_posture",
    "normalize_chromestats",
    "normalize_webstore_trust",
    "normalize_maintenance_health",
    # Privacy normalizers
    "normalize_permissions_baseline",
    "normalize_permission_combos",
    "normalize_network_exfil",
    "normalize_capture_signals",
    # Batch normalizers
    "normalize_security_factors",
    "normalize_privacy_factors",
    # Gates
    "GateResult",
    "GateConfig",
    "HardGates",
    "evaluate_hard_gates",
    "get_hard_gate_summary",
    # Engine
    "ScoringEngine",
    "calculate_extension_score",
    "get_score_explanation",
    # Explanation
    "ExplanationBuilder",
    "ExplanationPayload",
    "FactorExplanation",
    "LayerExplanation",
    "build_explanation",
    "get_ui_explanation",
]

