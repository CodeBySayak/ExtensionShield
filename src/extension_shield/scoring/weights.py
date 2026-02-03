"""
Versioned Weight Presets

Defines weight configurations for each scoring layer. Weights are versioned
to allow A/B testing and gradual rollout of weight changes.

Each weight set defines how much each factor contributes to its layer score.
Weights within a layer should sum to 1.0 for proper normalization.
"""

from dataclasses import dataclass
from typing import Dict, Optional


# =============================================================================
# SECURITY LAYER WEIGHTS (V1)
# =============================================================================
# Total: 1.0
# Factors focused on technical security vulnerabilities and threats

SECURITY_WEIGHTS_V1: Dict[str, float] = {
    "SAST": 0.30,           # Static analysis findings (highest impact on security)
    "VirusTotal": 0.15,     # Malware detection consensus
    "Obfuscation": 0.15,    # Code obfuscation detection
    "Manifest": 0.10,       # Manifest security configuration
    "ChromeStats": 0.10,    # Behavioral threat intelligence
    "Webstore": 0.10,       # Webstore reputation signals
    "Maintenance": 0.10,    # Maintenance health (stale = higher risk)
}


# =============================================================================
# PRIVACY LAYER WEIGHTS (V1)
# =============================================================================
# Total: 1.0
# Factors focused on data collection, permissions, and exfiltration risk

PRIVACY_WEIGHTS_V1: Dict[str, float] = {
    "PermissionsBaseline": 0.25,    # Individual permission risk assessment
    "PermissionCombos": 0.25,       # Dangerous permission combinations
    "NetworkExfil": 0.35,           # Network exfiltration patterns (highest privacy impact)
    "CaptureSignals": 0.15,         # Screenshot/tab capture detection
}


# =============================================================================
# GOVERNANCE LAYER WEIGHTS (V1)
# =============================================================================
# Total: 1.0
# Factors focused on policy compliance and organizational requirements

GOVERNANCE_WEIGHTS_V1: Dict[str, float] = {
    "ToSViolations": 0.50,          # Terms of service violations (highest governance impact)
    "Consistency": 0.30,            # Consistency between claimed and actual behavior
    "DisclosureAlignment": 0.20,    # Privacy policy and disclosure alignment
}


# =============================================================================
# LAYER WEIGHTS
# =============================================================================
# How much each layer contributes to the overall score
# Total: 1.0

LAYER_WEIGHTS: Dict[str, float] = {
    "security": 0.50,       # Security is primary concern
    "privacy": 0.30,        # Privacy is secondary but important
    "governance": 0.20,     # Governance for policy compliance
}


# =============================================================================
# WEIGHT PRESET MANAGEMENT
# =============================================================================

@dataclass(frozen=True)
class WeightPreset:
    """
    Immutable weight preset configuration.
    
    Contains all weight settings for a single version of the scoring engine.
    """
    
    version: str
    security_weights: Dict[str, float]
    privacy_weights: Dict[str, float]
    governance_weights: Dict[str, float]
    layer_weights: Dict[str, float]
    description: str = ""
    
    def validate(self) -> bool:
        """
        Validate that weights sum to approximately 1.0.
        
        Returns:
            True if valid, False otherwise
        """
        tolerance = 0.001
        
        sec_sum = sum(self.security_weights.values())
        if abs(sec_sum - 1.0) > tolerance:
            return False
        
        priv_sum = sum(self.privacy_weights.values())
        if abs(priv_sum - 1.0) > tolerance:
            return False
        
        gov_sum = sum(self.governance_weights.values())
        if abs(gov_sum - 1.0) > tolerance:
            return False
        
        layer_sum = sum(self.layer_weights.values())
        if abs(layer_sum - 1.0) > tolerance:
            return False
        
        return True
    
    def get_security_weight(self, factor_name: str) -> float:
        """Get weight for a security factor, defaulting to 0.0 if not found."""
        return self.security_weights.get(factor_name, 0.0)
    
    def get_privacy_weight(self, factor_name: str) -> float:
        """Get weight for a privacy factor, defaulting to 0.0 if not found."""
        return self.privacy_weights.get(factor_name, 0.0)
    
    def get_governance_weight(self, factor_name: str) -> float:
        """Get weight for a governance factor, defaulting to 0.0 if not found."""
        return self.governance_weights.get(factor_name, 0.0)


# =============================================================================
# PRESET REGISTRY
# =============================================================================

WEIGHT_PRESETS: Dict[str, WeightPreset] = {
    "v1": WeightPreset(
        version="1.0.0",
        security_weights=SECURITY_WEIGHTS_V1,
        privacy_weights=PRIVACY_WEIGHTS_V1,
        governance_weights=GOVERNANCE_WEIGHTS_V1,
        layer_weights=LAYER_WEIGHTS,
        description="Initial V2 scoring weights based on scoring_v2_design.md spec",
    ),
}

# Default preset
DEFAULT_PRESET = "v1"


def get_weight_preset(version: Optional[str] = None) -> WeightPreset:
    """
    Get a weight preset by version.
    
    Args:
        version: Preset version (e.g., "v1"). Defaults to DEFAULT_PRESET.
        
    Returns:
        WeightPreset configuration
        
    Raises:
        KeyError: If version not found in registry
    """
    preset_key = version or DEFAULT_PRESET
    if preset_key not in WEIGHT_PRESETS:
        raise KeyError(
            f"Weight preset '{preset_key}' not found. "
            f"Available: {list(WEIGHT_PRESETS.keys())}"
        )
    return WEIGHT_PRESETS[preset_key]


# =============================================================================
# FACTOR NAME CONSTANTS
# =============================================================================
# Use these constants when creating FactorScore instances to ensure consistency

class SecurityFactors:
    """Security layer factor names."""
    SAST = "SAST"
    VIRUSTOTAL = "VirusTotal"
    OBFUSCATION = "Obfuscation"
    MANIFEST = "Manifest"
    CHROMESTATS = "ChromeStats"
    WEBSTORE = "Webstore"
    MAINTENANCE = "Maintenance"


class PrivacyFactors:
    """Privacy layer factor names."""
    PERMISSIONS_BASELINE = "PermissionsBaseline"
    PERMISSION_COMBOS = "PermissionCombos"
    NETWORK_EXFIL = "NetworkExfil"
    CAPTURE_SIGNALS = "CaptureSignals"


class GovernanceFactors:
    """Governance layer factor names."""
    TOS_VIOLATIONS = "ToSViolations"
    CONSISTENCY = "Consistency"
    DISCLOSURE_ALIGNMENT = "DisclosureAlignment"

