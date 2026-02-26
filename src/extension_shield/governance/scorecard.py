"""
Layer 1: Security Scorecard

Deterministic scoring pipeline that consumes SignalPack (Layer 0) and produces
scored factors with points and confidence.

Factors:
- F_SAST_SEMGREP: SAST findings with test exclusion, deduping, severity weighting
- F_VIRUSTOTAL_CONSENSUS: Ratio-based VT scoring (not binary)
- F_ENTROPY_OBFUSCATION: Separate minified vs obfuscated
- F_MANIFEST_SECURITY: Manifest security issues
- F_NETWORK_BEHAVIOR_LITE: Network endpoint reputation (basic)
- F_WEBSTORE_REPUTATION_BEHAVIOR: Webstore stats + reviews with trend/manipulation awareness

Each factor outputs:
- points: Risk points (0 = no risk, higher = more risk)
- max_points: Maximum possible points for this factor
- confidence: Confidence in the score (0.0-1.0)
- details: Detailed breakdown
- evidence_ids: Related evidence IDs from SignalPack
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set, Tuple, TYPE_CHECKING

from .signal_pack import SignalPack, SastFindingNormalized

if TYPE_CHECKING:
    from .signal_pack import WebstoreStatsSignalPack, WebstoreReviewsSignalPack

logger = logging.getLogger(__name__)


# =============================================================================
# SCORECARD FACTOR RESULT
# =============================================================================


@dataclass
class FactorResult:
    """Result from a scorecard factor evaluation."""
    factor_id: str
    points: float
    max_points: float
    confidence: float
    details: Dict[str, Any] = field(default_factory=dict)
    evidence_ids: List[str] = field(default_factory=list)
    flags: List[str] = field(default_factory=list)
    
    @property
    def normalized_score(self) -> float:
        """Get normalized score (0-1, where 0 = no risk, 1 = max risk)."""
        if self.max_points == 0:
            return 0.0
        return min(1.0, self.points / self.max_points)
    
    @property
    def risk_level(self) -> str:
        """Get risk level based on normalized score."""
        score = self.normalized_score
        if score >= 0.7:
            return "critical"
        elif score >= 0.5:
            return "high"
        elif score >= 0.3:
            return "medium"
        elif score > 0:
            return "low"
        return "none"


@dataclass
class SecurityScorecard:
    """
    Complete security scorecard with all factor results.
    
    This is the output of Layer 1 processing.
    """
    scan_id: str
    factors: Dict[str, FactorResult] = field(default_factory=dict)
    total_points: float = 0.0
    max_possible_points: float = 0.0
    overall_confidence: float = 1.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    # V2 scoring container (optional, for serialization only - does not affect points-based scoring)
    v2: Optional[Dict[str, Any]] = None
    
    @property
    def security_score(self) -> int:
        """
        Calculate overall security score (0-100, where 100 = secure).
        
        Inverts risk points to create a security score.
        """
        if self.max_possible_points == 0:
            return 100
        
        # Cap at max and invert
        risk_ratio = min(1.0, self.total_points / self.max_possible_points)
        return int(100 * (1 - risk_ratio))
    
    @property
    def risk_level(self) -> str:
        """Overall risk level based on security score. Red: 0-49, Yellow: 50-74, Green: 75-100."""
        score = self.security_score
        if score < 40:
            return "critical"
        elif score < 50:
            return "high"
        elif score < 75:
            return "medium"
        return "low"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "scan_id": self.scan_id,
            "security_score": self.security_score,
            "risk_level": self.risk_level,
            "total_points": self.total_points,
            "max_possible_points": self.max_possible_points,
            "overall_confidence": self.overall_confidence,
            "factors": {
                factor_id: {
                    "factor_id": factor_result.factor_id,
                    "points": factor_result.points,
                    "max_points": factor_result.max_points,
                    "confidence": factor_result.confidence,
                    "normalized_score": factor_result.normalized_score,
                    "risk_level": factor_result.risk_level,
                    "details": factor_result.details,
                    "flags": factor_result.flags,
                    "evidence_ids": factor_result.evidence_ids,
                }
                for factor_id, factor_result in self.factors.items()
            },
            "created_at": self.created_at.isoformat(),
        }
        # Include v2 scoring if attached (Phase 2.2 - serialization only)
        if self.v2 is not None:
            result["v2"] = self.v2
        return result


# =============================================================================
# FACTOR: F_SAST_SEMGREP
# =============================================================================


class SastSemgrepFactor:
    """
    F_SAST_SEMGREP: SAST findings scoring with advanced filtering.
    
    Features:
    - Exclude test/build files
    - Dedupe repeated patterns
    - Severity weighting
    - Optional reachability heuristic
    """
    
    FACTOR_ID = "F_SAST_SEMGREP"
    MAX_POINTS = 60.0
    
    # Paths to exclude (tests, build artifacts, etc.)
    EXCLUDE_PATTERNS = [
        r"test[s]?/",
        r"__test__",
        r"\.test\.",
        r"\.spec\.",
        r"_test\.",
        r"_spec\.",
        r"build/",
        r"dist/",
        r"node_modules/",
        r"vendor/",
        r"\.min\.js$",
        r"bundle\.",
        r"webpack\.",
        r"coverage/",
        r"__mocks__/",
        r"fixtures?/",
    ]
    
    # Severity weights
    SEVERITY_WEIGHTS = {
        "CRITICAL": 15.0,
        "ERROR": 10.0,
        "HIGH": 10.0,
        "WARNING": 4.0,
        "MEDIUM": 4.0,
        "INFO": 1.0,
        "LOW": 1.0,
    }
    
    # Reachability boost for findings in main code paths
    REACHABLE_PATHS = [
        "background.js",
        "content.js",
        "service_worker.js",
        "popup.js",
        "main.js",
        "index.js",
        "app.js",
    ]
    
    def __init__(self):
        self._exclude_compiled = [re.compile(p, re.IGNORECASE) for p in self.EXCLUDE_PATTERNS]
    
    def _should_exclude(self, file_path: str) -> bool:
        """Check if file should be excluded from scoring."""
        for pattern in self._exclude_compiled:
            if pattern.search(file_path):
                return True
        return False
    
    def _is_reachable_path(self, file_path: str) -> bool:
        """Check if file is in a likely reachable code path."""
        file_name = file_path.split("/")[-1].lower()
        return any(rp.lower() in file_name for rp in self.REACHABLE_PATHS)
    
    def _dedupe_findings(
        self,
        findings: List[SastFindingNormalized],
    ) -> Tuple[List[SastFindingNormalized], int]:
        """
        Deduplicate findings by pattern.
        
        Returns:
            Tuple of (deduplicated findings, duplicate count)
        """
        # Key: (check_id, severity) -> first finding
        seen: Dict[str, SastFindingNormalized] = {}
        duplicates = 0
        
        for finding in findings:
            # Create dedup key from check_id + severity
            # This keeps one finding per unique rule+severity combo
            key = f"{finding.check_id}:{finding.severity}"
            
            if key not in seen:
                seen[key] = finding
            else:
                duplicates += 1
        
        return list(seen.values()), duplicates
    
    def evaluate(self, signal_pack: SignalPack) -> FactorResult:
        """Evaluate SAST findings and return scored result."""
        sast = signal_pack.sast
        
        if not sast.deduped_findings:
            return FactorResult(
                factor_id=self.FACTOR_ID,
                points=0.0,
                max_points=self.MAX_POINTS,
                confidence=sast.confidence,
                details={"message": "No SAST findings"},
            )
        
        # Filter out excluded files
        filtered_findings = []
        excluded_count = 0
        
        for finding in sast.deduped_findings:
            if self._should_exclude(finding.file_path):
                excluded_count += 1
            else:
                filtered_findings.append(finding)
        
        # Dedupe similar patterns
        deduped_findings, duplicate_count = self._dedupe_findings(filtered_findings)
        
        # Calculate weighted score
        points = 0.0
        severity_breakdown: Dict[str, int] = {}
        reachable_count = 0
        
        for finding in deduped_findings:
            severity = finding.severity.upper()
            weight = self.SEVERITY_WEIGHTS.get(severity, 1.0)
            
            # Reachability boost
            if self._is_reachable_path(finding.file_path):
                weight *= 1.25
                reachable_count += 1
            
            points += weight
            severity_breakdown[severity] = severity_breakdown.get(severity, 0) + 1
        
        # Bonus penalty for many critical findings
        critical_count = severity_breakdown.get("CRITICAL", 0)
        if critical_count >= 10:
            points += 20.0
        elif critical_count >= 5:
            points += 10.0
        
        # Cap at max points
        points = min(self.MAX_POINTS, points)
        
        # Get evidence IDs
        evidence_ids = [
            e.evidence_id for e in signal_pack.evidence
            if e.tool_name == "sast"
        ]
        
        return FactorResult(
            factor_id=self.FACTOR_ID,
            points=points,
            max_points=self.MAX_POINTS,
            confidence=sast.confidence,
            details={
                "total_findings": len(sast.deduped_findings),
                "filtered_findings": len(deduped_findings),
                "excluded_count": excluded_count,
                "duplicate_count": duplicate_count,
                "reachable_count": reachable_count,
                "severity_breakdown": severity_breakdown,
                "message": f"{len(deduped_findings)} findings after filtering ({excluded_count} excluded, {duplicate_count} deduped)",
            },
            evidence_ids=evidence_ids,
        )


# =============================================================================
# FACTOR: F_VIRUSTOTAL_CONSENSUS
# =============================================================================


class VirusTotalConsensusFactor:
    """
    F_VIRUSTOTAL_CONSENSUS: Ratio-based VirusTotal scoring.
    
    Uses detection ratios instead of binary all-or-nothing scoring.
    Considers vendor consensus and malware family diversity.
    """
    
    FACTOR_ID = "F_VIRUSTOTAL_CONSENSUS"
    MAX_POINTS = 50.0
    
    # Thresholds for ratio-based scoring
    MALICIOUS_RATIO_THRESHOLDS = [
        (0.5, 50.0),   # >= 50% engines: max points
        (0.3, 40.0),   # >= 30% engines: 40 points
        (0.1, 25.0),   # >= 10% engines: 25 points
        (0.05, 15.0),  # >= 5% engines: 15 points
        (0.01, 8.0),   # >= 1% engines: 8 points
        (0.0, 0.0),    # No detections: 0 points
    ]
    
    SUSPICIOUS_RATIO_WEIGHT = 0.3  # Suspicious = 30% of malicious weight
    
    def evaluate(self, signal_pack: SignalPack) -> FactorResult:
        """Evaluate VirusTotal results with ratio-based scoring."""
        vt = signal_pack.virustotal
        
        if not vt.enabled:
            return FactorResult(
                factor_id=self.FACTOR_ID,
                points=0.0,
                max_points=self.MAX_POINTS,
                confidence=0.5,  # Low confidence when not enabled
                details={"message": "VirusTotal not enabled"},
            )
        
        if vt.total_engines == 0:
            return FactorResult(
                factor_id=self.FACTOR_ID,
                points=0.0,
                max_points=self.MAX_POINTS,
                confidence=0.5,
                details={"message": "No VirusTotal engine results"},
            )
        
        # Calculate ratios
        malicious_ratio = vt.malicious_count / vt.total_engines
        suspicious_ratio = vt.suspicious_count / vt.total_engines
        
        # Get base points from malicious ratio
        base_points = 0.0
        for threshold, pts in self.MALICIOUS_RATIO_THRESHOLDS:
            if malicious_ratio >= threshold:
                base_points = pts
                break
        
        # Add weighted suspicious points
        suspicious_points = 0.0
        for threshold, pts in self.MALICIOUS_RATIO_THRESHOLDS:
            if suspicious_ratio >= threshold:
                suspicious_points = pts * self.SUSPICIOUS_RATIO_WEIGHT
                break
        
        points = min(self.MAX_POINTS, base_points + suspicious_points)
        
        # Confidence based on number of engines and consensus
        confidence = min(1.0, vt.total_engines / 70)  # Full confidence at 70+ engines
        
        # Bonus for diverse malware family detection
        family_count = len(vt.malware_families)
        if family_count >= 5:
            points = min(self.MAX_POINTS, points * 1.15)  # 15% boost
        
        # Get evidence IDs
        evidence_ids = [
            e.evidence_id for e in signal_pack.evidence
            if e.tool_name == "virustotal"
        ]
        
        flags = []
        if malicious_ratio >= 0.1:
            flags.append("high_detection_consensus")
        if family_count >= 3:
            flags.append("multiple_malware_families")
        
        return FactorResult(
            factor_id=self.FACTOR_ID,
            points=points,
            max_points=self.MAX_POINTS,
            confidence=confidence,
            details={
                "malicious_count": vt.malicious_count,
                "suspicious_count": vt.suspicious_count,
                "total_engines": vt.total_engines,
                "malicious_ratio": round(malicious_ratio, 4),
                "suspicious_ratio": round(suspicious_ratio, 4),
                "malware_families": vt.malware_families[:10],
                "family_count": family_count,
                "threat_level": vt.threat_level,
                "message": f"{vt.malicious_count}/{vt.total_engines} engines ({malicious_ratio:.1%}) detected malicious",
            },
            evidence_ids=evidence_ids,
            flags=flags,
        )


# =============================================================================
# FACTOR: F_ENTROPY_OBFUSCATION
# =============================================================================


class EntropyObfuscationFactor:
    """
    F_ENTROPY_OBFUSCATION: Entropy-based obfuscation detection.
    
    Separates minified files (acceptable) from obfuscated files (suspicious).
    Uses entropy thresholds and pattern detection.
    """
    
    FACTOR_ID = "F_ENTROPY_OBFUSCATION"
    MAX_POINTS = 30.0
    
    # Known minification patterns (not suspicious)
    MINIFIED_INDICATORS = [
        r"\.min\.js$",
        r"\.bundle\.js$",
        r"\.prod\.js$",
        r"-min\.js$",
        r"\.compressed\.js$",
    ]
    
    # Obfuscation patterns (suspicious)
    OBFUSCATION_PATTERNS = [
        "eval_usage",
        "function_constructor",
        "jsfuck_pattern",
        "packed_code",
        "obfuscator_io",
    ]
    
    def __init__(self):
        self._minified_compiled = [re.compile(p, re.IGNORECASE) for p in self.MINIFIED_INDICATORS]
    
    def _is_likely_minified(self, file_path: str) -> bool:
        """Check if file name indicates minification."""
        for pattern in self._minified_compiled:
            if pattern.search(file_path):
                return True
        return False
    
    def evaluate(self, signal_pack: SignalPack) -> FactorResult:
        """Evaluate entropy/obfuscation with minified/obfuscated separation."""
        entropy = signal_pack.entropy
        
        if entropy.files_analyzed == 0:
            return FactorResult(
                factor_id=self.FACTOR_ID,
                points=0.0,
                max_points=self.MAX_POINTS,
                confidence=0.5,
                details={"message": "No files analyzed for entropy"},
            )
        
        # Categorize suspected files
        true_obfuscated: List[str] = []
        minified_only: List[str] = []
        
        for file_path in entropy.suspected_obfuscation_files:
            if self._is_likely_minified(file_path):
                minified_only.append(file_path)
            else:
                true_obfuscated.append(file_path)
        
        # Also check files in minified_files list
        for file_path in entropy.minified_files:
            if file_path not in minified_only:
                minified_only.append(file_path)
        
        # Score based on true obfuscation (not just minification)
        points = 0.0
        
        # Points per obfuscated file (diminishing returns)
        for i, _ in enumerate(true_obfuscated):
            if i < 2:
                points += 10.0
            elif i < 5:
                points += 5.0
            else:
                points += 2.0
        
        # Bonus for high-risk patterns
        high_risk_pattern_count = sum(entropy.high_risk_patterns.values())
        if high_risk_pattern_count >= 5:
            points += 10.0
        elif high_risk_pattern_count >= 2:
            points += 5.0
        
        # Mild penalty for minified files (could hide issues)
        if len(minified_only) > 5:
            points += 2.0
        
        points = min(self.MAX_POINTS, points)
        
        # Confidence based on analysis coverage
        confidence = 0.8 if entropy.files_analyzed >= 5 else 0.6
        
        # Get evidence IDs
        evidence_ids = [
            e.evidence_id for e in signal_pack.evidence
            if e.tool_name == "entropy"
        ]
        
        flags = []
        if true_obfuscated:
            flags.append("obfuscation_detected")
        if high_risk_pattern_count >= 3:
            flags.append("high_risk_patterns")
        
        return FactorResult(
            factor_id=self.FACTOR_ID,
            points=points,
            max_points=self.MAX_POINTS,
            confidence=confidence,
            details={
                "files_analyzed": entropy.files_analyzed,
                "obfuscated_count": len(true_obfuscated),
                "minified_count": len(minified_only),
                "obfuscated_files": true_obfuscated[:5],
                "minified_files": minified_only[:5],
                "high_risk_patterns": entropy.high_risk_patterns,
                "overall_risk": entropy.overall_risk,
                "message": f"{len(true_obfuscated)} obfuscated, {len(minified_only)} minified files",
            },
            evidence_ids=evidence_ids,
            flags=flags,
        )


# =============================================================================
# FACTOR: F_MANIFEST_SECURITY
# =============================================================================


class ManifestSecurityFactor:
    """
    F_MANIFEST_SECURITY: Manifest security configuration scoring.
    
    Evaluates:
    - Content Security Policy
    - Manifest version
    - Permissions configuration
    - Update URL security
    """
    
    FACTOR_ID = "F_MANIFEST_SECURITY"
    MAX_POINTS = 20.0
    
    # High-risk host patterns
    BROAD_HOST_PATTERNS = {"<all_urls>", "*://*/*", "http://*/*", "https://*/*"}
    
    # Sensitive permissions
    SENSITIVE_PERMISSIONS = {
        "debugger": 8.0,
        "webRequest": 5.0,
        "webRequestBlocking": 6.0,
        "proxy": 7.0,
        "nativeMessaging": 6.0,
        "cookies": 4.0,
        "history": 4.0,
        "browsingData": 5.0,
        "management": 5.0,
        "desktopCapture": 6.0,
        "tabCapture": 5.0,
        "clipboardRead": 4.0,
    }
    
    def evaluate(self, signal_pack: SignalPack) -> FactorResult:
        """Evaluate manifest security configuration."""
        perms = signal_pack.permissions
        
        points = 0.0
        issues: List[str] = []
        
        # Check broad host permissions
        if perms.has_broad_host_access:
            points += 8.0
            issues.append(f"Broad host access: {', '.join(perms.broad_host_patterns)}")
        
        # Check sensitive permissions
        sensitive_found: Dict[str, float] = {}
        for perm in perms.api_permissions:
            if perm in self.SENSITIVE_PERMISSIONS:
                weight = self.SENSITIVE_PERMISSIONS[perm]
                sensitive_found[perm] = weight
                points += weight * 0.5  # Half weight for declared permissions
        
        # Extra penalty for unreasonable sensitive permissions
        for perm in perms.unreasonable_permissions:
            if perm in self.SENSITIVE_PERMISSIONS:
                points += self.SENSITIVE_PERMISSIONS[perm] * 0.5
                issues.append(f"Unreasonable sensitive permission: {perm}")
        
        # Check for high-risk permission count
        if len(perms.high_risk_permissions) >= 3:
            points += 5.0
            issues.append(f"{len(perms.high_risk_permissions)} high-risk permissions")
        
        points = min(self.MAX_POINTS, points)
        
        # Get evidence IDs
        evidence_ids = [
            e.evidence_id for e in signal_pack.evidence
            if e.tool_name == "permissions"
        ]
        
        flags = []
        if perms.has_broad_host_access:
            flags.append("broad_host_access")
        if len(sensitive_found) >= 3:
            flags.append("multiple_sensitive_permissions")
        
        return FactorResult(
            factor_id=self.FACTOR_ID,
            points=points,
            max_points=self.MAX_POINTS,
            confidence=0.95,  # High confidence for manifest analysis
            details={
                "total_permissions": perms.total_permissions,
                "api_permissions": perms.api_permissions,
                "host_permissions": perms.host_permissions,
                "sensitive_permissions": list(sensitive_found.keys()),
                "unreasonable_permissions": perms.unreasonable_permissions,
                "high_risk_permissions": perms.high_risk_permissions,
                "broad_host_patterns": perms.broad_host_patterns,
                "issues": issues,
                "message": f"{perms.total_permissions} permissions, {len(issues)} security issues",
            },
            evidence_ids=evidence_ids,
            flags=flags,
        )


# =============================================================================
# FACTOR: F_NETWORK_BEHAVIOR_LITE
# =============================================================================


class NetworkBehaviorLiteFactor:
    """
    F_NETWORK_BEHAVIOR_LITE: Basic network endpoint reputation scoring.
    
    Evaluates network-related SAST findings and permission combinations
    that indicate external communication.
    """
    
    FACTOR_ID = "F_NETWORK_BEHAVIOR_LITE"
    MAX_POINTS = 15.0
    
    # Suspicious domain patterns
    SUSPICIOUS_DOMAIN_PATTERNS = [
        r"\.tk$",
        r"\.ml$",
        r"\.ga$",
        r"\.cf$",
        r"\.gq$",
        r"bit\.ly",
        r"tinyurl",
        r"pastebin",
        r"discord\.gg",
        r"telegra\.ph",
    ]
    
    # Network-related SAST finding patterns
    NETWORK_FINDING_PATTERNS = [
        "fetch",
        "xhr",
        "ajax",
        "http",
        "endpoint",
        "external_api",
        "third_party",
        "network",
        "websocket",
        "beacon",
    ]
    
    def __init__(self):
        self._suspicious_compiled = [re.compile(p, re.IGNORECASE) for p in self.SUSPICIOUS_DOMAIN_PATTERNS]
    
    def _check_suspicious_domain(self, text: str) -> List[str]:
        """Check for suspicious domain patterns in text."""
        matches = []
        for pattern in self._suspicious_compiled:
            if pattern.search(text):
                matches.append(pattern.pattern)
        return matches
    
    def evaluate(self, signal_pack: SignalPack) -> FactorResult:
        """Evaluate network behavior patterns."""
        sast = signal_pack.sast
        perms = signal_pack.permissions
        
        points = 0.0
        network_findings: List[str] = []
        suspicious_domains: List[str] = []
        
        # Check for network-related SAST findings
        for finding in sast.deduped_findings:
            check_id_lower = finding.check_id.lower()
            message_lower = finding.message.lower()
            
            for pattern in self.NETWORK_FINDING_PATTERNS:
                if pattern in check_id_lower or pattern in message_lower:
                    network_findings.append(finding.check_id)
                    
                    # Check for suspicious domains in the finding
                    snippet = finding.code_snippet or ""
                    suspicious = self._check_suspicious_domain(snippet)
                    suspicious_domains.extend(suspicious)
                    break
        
        # Dedupe findings
        network_findings = list(set(network_findings))
        suspicious_domains = list(set(suspicious_domains))
        
        # Score based on network findings
        if network_findings:
            points += min(8.0, len(network_findings) * 2.0)
        
        # Extra points for suspicious domains
        if suspicious_domains:
            points += min(5.0, len(suspicious_domains) * 2.5)
        
        # Check for risky permission combinations
        has_webrequest = "webRequest" in perms.api_permissions
        has_broad_host = perms.has_broad_host_access
        has_storage = "storage" in perms.api_permissions
        
        if has_webrequest and has_broad_host:
            points += 4.0  # Can intercept all traffic
        
        if has_storage and network_findings:
            points += 2.0  # Can exfiltrate stored data
        
        points = min(self.MAX_POINTS, points)
        
        # Confidence based on data availability
        confidence = 0.7 if network_findings else 0.5
        
        flags = []
        if suspicious_domains:
            flags.append("suspicious_domains")
        if has_webrequest and has_broad_host:
            flags.append("traffic_interception_capability")
        
        return FactorResult(
            factor_id=self.FACTOR_ID,
            points=points,
            max_points=self.MAX_POINTS,
            confidence=confidence,
            details={
                "network_findings_count": len(network_findings),
                "network_findings": network_findings[:10],
                "suspicious_domains": suspicious_domains,
                "has_webrequest": has_webrequest,
                "has_broad_host": has_broad_host,
                "has_storage": has_storage,
                "message": f"{len(network_findings)} network findings, {len(suspicious_domains)} suspicious domains",
            },
            flags=flags,
        )


# =============================================================================
# FACTOR: F_WEBSTORE_REPUTATION_BEHAVIOR
# =============================================================================


class WebstoreReputationBehaviorFactor:
    """
    F_WEBSTORE_REPUTATION_BEHAVIOR: Webstore stats + reviews with trend/manipulation awareness.
    
    Features:
    - Trend-aware: Spikes in negative reviews increase risk
    - Manipulation-aware: Detects fake review patterns
    - Complaint keyword clustering for security/privacy issues
    - Distinguishes generic complaints vs security complaints
    
    IMPORTANT: Reviews are treated as a NOISY SIGNAL:
    - Lower confidence by default (max 0.6 for reviews alone)
    - Used to push borderline cases into WARN, not hard BLOCK
    - Only high confidence when strong trend + specific allegations
    """
    
    FACTOR_ID = "F_WEBSTORE_REPUTATION_BEHAVIOR"
    MAX_POINTS = 25.0
    
    # Maximum confidence for review-based signals (reviews are noisy)
    MAX_REVIEW_CONFIDENCE = 0.6
    # Confidence boost for specific security allegations
    SECURITY_ALLEGATION_CONFIDENCE_BOOST = 0.2
    
    # Security/privacy complaint keywords (high severity)
    SECURITY_COMPLAINT_KEYWORDS = {
        "steals data": 8.0,
        "stealing data": 8.0,
        "logs in": 6.0,
        "password": 7.0,
        "cookie": 6.0,
        "hijack": 8.0,
        "redirect": 5.0,
        "adware": 7.0,
        "malware": 9.0,
        "virus": 8.0,
        "spyware": 8.0,
        "tracking": 5.0,
        "privacy": 4.0,
        "suspicious": 4.0,
        "phishing": 8.0,
        "scam": 7.0,
        "hack": 7.0,
        "stolen": 7.0,
        "credential": 7.0,
        "inject": 6.0,
        "keylogger": 9.0,
        "bitcoin": 5.0,
        "crypto": 4.0,
        "mining": 6.0,
    }
    
    # Generic complaint keywords (low severity)
    GENERIC_COMPLAINT_KEYWORDS = {
        "doesn't work": 1.0,
        "not working": 1.0,
        "broken": 1.0,
        "crash": 1.0,
        "slow": 0.5,
        "buggy": 1.0,
        "useless": 0.5,
        "waste": 0.5,
    }
    
    # Manipulation indicators
    MANIPULATION_PATTERNS = [
        "extremely_low_review_ratio",
        "review_spike",
        "repetitive_reviews",
        "fake_reviews",
    ]
    
    def _analyze_keyword_hits(
        self,
        keyword_hits: Dict[str, int],
    ) -> Tuple[float, List[str], List[str]]:
        """
        Analyze keyword hits for security vs generic complaints.
        
        Returns:
            Tuple of (points, security_keywords, generic_keywords)
        """
        points = 0.0
        security_keywords: List[str] = []
        generic_keywords: List[str] = []
        
        for keyword, count in keyword_hits.items():
            keyword_lower = keyword.lower()
            
            # Check security keywords
            for sec_kw, weight in self.SECURITY_COMPLAINT_KEYWORDS.items():
                if sec_kw in keyword_lower:
                    points += weight * min(count, 3)  # Cap per-keyword contribution
                    security_keywords.append(f"{keyword} ({count})")
                    break
            else:
                # Check generic keywords
                for gen_kw, weight in self.GENERIC_COMPLAINT_KEYWORDS.items():
                    if gen_kw in keyword_lower:
                        # Generic complaints add minimal points
                        points += weight * min(count, 2)
                        generic_keywords.append(f"{keyword} ({count})")
                        break
        
        return points, security_keywords, generic_keywords
    
    def _check_manipulation(
        self,
        stats: "WebstoreStatsSignalPack",
        reviews: "WebstoreReviewsSignalPack",
    ) -> Tuple[float, List[str], float]:
        """
        Check for review manipulation patterns.
        
        Returns:
            Tuple of (points, flags, confidence_penalty)
        """
        points = 0.0
        flags: List[str] = []
        confidence_penalty = 0.0
        
        # Check for existing manipulation flags
        for flag in reviews.manipulation_flags:
            if flag in self.MANIPULATION_PATTERNS:
                points += 3.0
                flags.append(flag)
                confidence_penalty += 0.1
        
        # Check review-to-install ratio (extremely low = suspicious)
        if stats.installs and stats.rating_count:
            ratio = stats.rating_count / stats.installs
            if ratio < 0.0001:  # Less than 0.01%
                points += 4.0
                flags.append("extremely_low_review_ratio")
                confidence_penalty += 0.15
        
        # Check for rating manipulation (high rating + low count)
        if stats.rating_avg and stats.rating_count:
            if stats.rating_avg >= 4.8 and stats.rating_count < 20:
                points += 2.0
                flags.append("possible_rating_inflation")
                confidence_penalty += 0.1
        
        return points, flags, confidence_penalty
    
    def _check_trust_signals(
        self,
        stats: "WebstoreStatsSignalPack",
    ) -> Tuple[float, List[str]]:
        """
        Check basic trust signals from webstore stats.
        
        Returns:
            Tuple of (points, issues)
        """
        points = 0.0
        issues: List[str] = []
        
        # Low install count
        if stats.installs is not None:
            if stats.installs < 100:
                points += 5.0
                issues.append(f"Very low installs: {stats.installs}")
            elif stats.installs < 1000:
                points += 3.0
                issues.append(f"Low installs: {stats.installs}")
        
        # Low rating
        if stats.rating_avg is not None:
            if stats.rating_avg < 2.5:
                points += 5.0
                issues.append(f"Very low rating: {stats.rating_avg}")
            elif stats.rating_avg < 3.5:
                points += 3.0
                issues.append(f"Low rating: {stats.rating_avg}")
        
        # Missing privacy policy
        if not stats.has_privacy_policy:
            points += 2.0
            issues.append("No privacy policy")
        
        # Check developer profile
        if not stats.developer_website:
            points += 1.0
            issues.append("No developer website")
        
        # Check for featured/best practices
        if not stats.follows_best_practices and not stats.is_featured:
            points += 1.0
        
        return points, issues
    
    def evaluate(self, signal_pack: SignalPack) -> FactorResult:
        """
        Evaluate webstore reputation and review behavior.
        
        IMPORTANT: Reviews are treated as a NOISY SIGNAL:
        - Base confidence is capped at MAX_REVIEW_CONFIDENCE (0.6)
        - Only boosted if there are specific security allegations
        - Points are reduced by confidence factor to prevent over-weighting
        """
        stats = signal_pack.webstore_stats
        reviews = signal_pack.webstore_reviews
        
        # Check trust signals (more reliable than reviews)
        trust_points, trust_issues = self._check_trust_signals(stats)
        
        # Analyze keyword hits for security vs generic complaints
        keyword_points, security_keywords, generic_keywords = self._analyze_keyword_hits(
            reviews.keyword_hits
        )
        
        # Check for manipulation
        manipulation_points, manipulation_flags, confidence_penalty = self._check_manipulation(
            stats, reviews
        )
        
        # =====================================================================
        # NOISY SIGNAL HANDLING: Reviews get lower confidence
        # =====================================================================
        
        # Trust signals (installs, rating, privacy policy) are more reliable
        trust_confidence = 0.85 if stats.installs and stats.installs > 10000 else 0.7
        
        # Review-based signals start with low confidence
        review_confidence = self.MAX_REVIEW_CONFIDENCE  # 0.6 base
        
        # Boost confidence only if we have SPECIFIC security allegations
        has_strong_allegations = len(security_keywords) >= 2 and any(
            kw.lower() in ["steals data", "malware", "keylogger", "phishing", "hijack"]
            for kw in [k.split(" (")[0] for k in security_keywords]  # Extract keyword without count
        )
        
        if has_strong_allegations:
            review_confidence = min(0.8, review_confidence + self.SECURITY_ALLEGATION_CONFIDENCE_BOOST)
        
        # Apply confidence penalty for manipulation suspicion
        review_confidence = max(0.3, review_confidence - confidence_penalty)
        
        # Weight the points by signal reliability
        # Trust signals are weighted at their confidence
        # Review signals are weighted lower (noisy)
        weighted_trust_points = trust_points * trust_confidence
        weighted_review_points = (keyword_points + manipulation_points) * review_confidence
        
        # Total points (capped)
        raw_points = trust_points + keyword_points + manipulation_points
        effective_points = min(self.MAX_POINTS, weighted_trust_points + weighted_review_points)
        
        # Overall confidence is weighted average
        total_weight = trust_points + keyword_points + manipulation_points
        if total_weight > 0:
            overall_confidence = (
                (trust_points * trust_confidence + 
                 (keyword_points + manipulation_points) * review_confidence)
                / total_weight
            )
        else:
            overall_confidence = 0.5
        
        # Get evidence IDs
        evidence_ids = [
            e.evidence_id for e in signal_pack.evidence
            if e.tool_name in ("webstore_stats", "webstore_reviews")
        ]
        
        # Compile flags
        flags = list(manipulation_flags)
        if security_keywords:
            flags.append("security_complaints_detected")
        if trust_points >= 5:
            flags.append("low_trust_signals")
        
        # Add recommendation based on signal strength
        recommendation = self._get_recommendation(
            effective_points, overall_confidence, security_keywords, manipulation_flags
        )
        
        return FactorResult(
            factor_id=self.FACTOR_ID,
            points=effective_points,
            max_points=self.MAX_POINTS,
            confidence=overall_confidence,
            details={
                # Stats
                "installs": stats.installs,
                "rating_avg": stats.rating_avg,
                "rating_count": stats.rating_count,
                "has_privacy_policy": stats.has_privacy_policy,
                "developer": stats.developer,
                # Complaints analysis
                "security_complaints": security_keywords,
                "generic_complaints": generic_keywords,
                "has_strong_allegations": has_strong_allegations,
                # Trust analysis
                "trust_issues": trust_issues,
                "trust_confidence": trust_confidence,
                # Manipulation analysis
                "manipulation_flags": manipulation_flags,
                "review_confidence": review_confidence,
                # Point breakdown
                "raw_points": raw_points,
                "trust_points": trust_points,
                "keyword_points": keyword_points,
                "manipulation_points": manipulation_points,
                "weighted_trust_points": weighted_trust_points,
                "weighted_review_points": weighted_review_points,
                # Recommendation
                "recommendation": recommendation,
                "is_noisy_signal": True,  # Flag for UI
                "message": f"Trust: {trust_points:.1f}pts (conf={trust_confidence:.0%}), Reviews: {keyword_points:.1f}pts (conf={review_confidence:.0%})",
            },
            evidence_ids=evidence_ids,
            flags=flags,
        )
    
    def _get_recommendation(
        self,
        points: float,
        confidence: float,
        security_keywords: List[str],
        manipulation_flags: List[str],
    ) -> str:
        """
        Get recommendation based on signal strength.
        
        Reviews are noisy - use for WARN, not BLOCK (unless policy dictates).
        """
        # Low confidence = not enough to act on
        if confidence < 0.5:
            return "LOW_CONFIDENCE_SIGNAL"
        
        # High points but security complaints = WARN
        if points >= 15 and security_keywords:
            return "WARN_SECURITY_COMPLAINTS"
        
        # Manipulation suspected = WARN
        if manipulation_flags:
            return "WARN_MANIPULATION_SUSPECTED"
        
        # Moderate points = WARN for borderline
        if points >= 10:
            return "WARN_LOW_TRUST"
        
        # Low points = OK
        if points >= 5:
            return "INFO_MINOR_CONCERNS"
        
        return "OK"


# =============================================================================
# FACTOR: F_CHROMESTATS_BEHAVIOR
# =============================================================================


class ChromeStatsBehaviorFactor:
    """
    F_CHROMESTATS_BEHAVIOR: Behavioral threat intelligence from ChromeStats.
    
    Uses historical behavioral data to detect anomalous patterns.
    """
    
    FACTOR_ID = "F_CHROMESTATS_BEHAVIOR"
    MAX_POINTS = 20.0
    
    def evaluate(self, signal_pack: SignalPack) -> FactorResult:
        """Evaluate ChromeStats behavioral data."""
        cs = signal_pack.chromestats
        
        if not cs.enabled:
            return FactorResult(
                factor_id=self.FACTOR_ID,
                points=0.0,
                max_points=self.MAX_POINTS,
                confidence=0.5,
                details={"message": "ChromeStats not enabled"},
            )
        
        # Use the pre-calculated risk score from the adapter
        # Scale it to our max points
        risk_ratio = min(1.0, cs.total_risk_score / 28)  # 28 is original max
        points = risk_ratio * self.MAX_POINTS
        
        # Confidence based on data quality
        confidence = 0.8 if cs.total_risk_score > 0 else 0.6
        
        # Get evidence IDs
        evidence_ids = [
            e.evidence_id for e in signal_pack.evidence
            if e.tool_name == "chromestats"
        ]
        
        flags = []
        if cs.overall_risk_level in ("high", "critical"):
            flags.append(f"chromestats_{cs.overall_risk_level}")
        
        return FactorResult(
            factor_id=self.FACTOR_ID,
            points=points,
            max_points=self.MAX_POINTS,
            confidence=confidence,
            details={
                "overall_risk_level": cs.overall_risk_level,
                "total_risk_score": cs.total_risk_score,
                "risk_indicators": cs.risk_indicators[:5],
                "install_trends": cs.install_trends,
                "rating_patterns": cs.rating_patterns,
                "message": f"ChromeStats risk: {cs.overall_risk_level} ({cs.total_risk_score} points)",
            },
            evidence_ids=evidence_ids,
            flags=flags,
        )


# =============================================================================
# GOVERNANCE SCORECARD
# =============================================================================


class GovernanceScorecard:
    """
    Layer 1: Governance Scorecard
    
    Focuses on governance-level decisions (ALLOW/BLOCK/WARN) based on
    security scorecard and policy considerations.
    
    Separates technical risk (SecurityScorecard) from governance decisions.
    Uses signals appropriately:
    - High-confidence signals (SAST, VT) can drive BLOCK
    - Low-confidence signals (reviews) drive WARN for borderline cases
    """
    
    # Thresholds for governance decisions
    BLOCK_THRESHOLD = 30  # Security score below this = BLOCK
    WARN_THRESHOLD = 60   # Security score below this = WARN
    
    # Factors that can trigger hard BLOCK (high confidence)
    BLOCKING_FACTORS = {
        "F_VIRUSTOTAL_CONSENSUS",  # Malware detection
        "F_SAST_SEMGREP",          # Critical security issues
    }
    
    # Factors that can only push to WARN (noisy signals)
    WARN_ONLY_FACTORS = {
        "F_WEBSTORE_REPUTATION_BEHAVIOR",  # Reviews are noisy
    }
    
    # Minimum confidence to consider a factor for BLOCK
    BLOCK_CONFIDENCE_THRESHOLD = 0.7
    
    def __init__(
        self,
        scan_id: str,
        security_scorecard: SecurityScorecard,
    ):
        self.scan_id = scan_id
        self.security_scorecard = security_scorecard
        self.verdict: str = "ALLOW"
        self.verdict_reasons: List[str] = []
        self.blocking_factors: List[str] = []
        self.warning_factors: List[str] = []
        self.confidence: float = 1.0
        self.recommendation: str = ""
        # V2 scoring container (optional, for serialization only - does not affect verdict logic)
        self.v2: Optional[Dict[str, Any]] = None
        
        # Compute the governance decision
        self._compute()
    
    def _compute(self) -> None:
        """Compute the governance verdict from security scorecard."""
        scorecard = self.security_scorecard
        
        # Collect high-risk factors
        critical_factors: List[Tuple[str, FactorResult]] = []
        warning_factors: List[Tuple[str, FactorResult]] = []
        
        for factor_id, result in scorecard.factors.items():
            # Skip low-risk factors
            if result.normalized_score < 0.3:
                continue
            
            # Check if this factor can trigger BLOCK
            is_blocking_factor = factor_id in self.BLOCKING_FACTORS
            is_warn_only = factor_id in self.WARN_ONLY_FACTORS
            has_high_confidence = result.confidence >= self.BLOCK_CONFIDENCE_THRESHOLD
            
            if is_blocking_factor and has_high_confidence and result.normalized_score >= 0.5:
                critical_factors.append((factor_id, result))
            elif is_warn_only or result.normalized_score >= 0.3:
                warning_factors.append((factor_id, result))
        
        # Determine verdict based on factors and overall score
        security_score = scorecard.security_score
        
        # BLOCK: Critical factors with high confidence OR very low score
        if critical_factors:
            self.verdict = "BLOCK"
            self.blocking_factors = [f[0] for f in critical_factors]
            for factor_id, result in critical_factors:
                self.verdict_reasons.append(
                    f"{factor_id}: {result.details.get('message', 'High risk detected')} "
                    f"(score={result.normalized_score:.0%}, confidence={result.confidence:.0%})"
                )
        elif security_score < self.BLOCK_THRESHOLD:
            self.verdict = "BLOCK"
            self.verdict_reasons.append(
                f"Security score {security_score}/100 below BLOCK threshold ({self.BLOCK_THRESHOLD})"
            )
        # WARN: Warning factors or borderline score
        elif warning_factors or security_score < self.WARN_THRESHOLD:
            self.verdict = "NEEDS_REVIEW"
            self.warning_factors = [f[0] for f in warning_factors]
            for factor_id, result in warning_factors:
                reason = result.details.get("recommendation", result.details.get("message", ""))
                self.verdict_reasons.append(
                    f"{factor_id}: {reason} (confidence={result.confidence:.0%})"
                )
            if security_score < self.WARN_THRESHOLD:
                self.verdict_reasons.append(
                    f"Security score {security_score}/100 below WARN threshold ({self.WARN_THRESHOLD})"
                )
        # ALLOW: No significant issues
        else:
            self.verdict = "ALLOW"
            self.verdict_reasons.append(
                f"Security score {security_score}/100 - no significant issues detected"
            )
        
        # Calculate overall confidence
        if critical_factors or warning_factors:
            all_factors = critical_factors + warning_factors
            self.confidence = sum(f[1].confidence for f in all_factors) / len(all_factors)
        else:
            self.confidence = scorecard.overall_confidence
        
        # Generate recommendation
        self._generate_recommendation()
    
    def _generate_recommendation(self) -> None:
        """Generate human-readable recommendation."""
        if self.verdict == "BLOCK":
            self.recommendation = (
                f"Extension should be BLOCKED. "
                f"Reasons: {'; '.join(self.verdict_reasons[:3])}"
            )
        elif self.verdict == "NEEDS_REVIEW":
            self.recommendation = (
                f"Extension requires manual REVIEW before approval. "
                f"Concerns: {'; '.join(self.verdict_reasons[:3])}"
            )
        else:
            self.recommendation = (
                f"Extension can be ALLOWED. "
                f"Security score: {self.security_scorecard.security_score}/100"
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        # Get webstore reputation details for UI
        webstore_factor = self.security_scorecard.factors.get("F_WEBSTORE_REPUTATION_BEHAVIOR")
        webstore_details = None
        if webstore_factor:
            webstore_details = {
                "points": webstore_factor.points,
                "max_points": webstore_factor.max_points,
                "confidence": webstore_factor.confidence,
                "is_noisy_signal": webstore_factor.details.get("is_noisy_signal", True),
                "security_complaints": webstore_factor.details.get("security_complaints", []),
                "generic_complaints": webstore_factor.details.get("generic_complaints", []),
                "manipulation_flags": webstore_factor.details.get("manipulation_flags", []),
                "trust_issues": webstore_factor.details.get("trust_issues", []),
                "recommendation": webstore_factor.details.get("recommendation", ""),
                "flags": webstore_factor.flags,
            }
        
        result = {
            "scan_id": self.scan_id,
            "verdict": self.verdict,
            "verdict_reasons": self.verdict_reasons,
            "blocking_factors": self.blocking_factors,
            "warning_factors": self.warning_factors,
            "confidence": self.confidence,
            "recommendation": self.recommendation,
            "security_score": self.security_scorecard.security_score,
            "security_risk_level": self.security_scorecard.risk_level,
            # Include webstore reputation for UI "why" explanation
            "webstore_reputation_behavior": webstore_details,
        }
        # Include v2 scoring if attached (Phase 2.2 - serialization only)
        if self.v2 is not None:
            result["v2"] = self.v2
        return result
    
    @classmethod
    def compute(cls, signal_pack: SignalPack, security_scorecard: SecurityScorecard) -> "GovernanceScorecard":
        """
        Factory method to compute governance scorecard.
        
        Args:
            signal_pack: Layer 0 SignalPack
            security_scorecard: Layer 1 SecurityScorecard
            
        Returns:
            GovernanceScorecard with verdict
        """
        return cls(
            scan_id=signal_pack.scan_id,
            security_scorecard=security_scorecard,
        )


# =============================================================================
# SCORECARD BUILDER
# =============================================================================


class ScorecardBuilder:
    """
    Builds a complete SecurityScorecard from a SignalPack.
    
    Orchestrates all factor evaluations and aggregates results.
    """
    
    def __init__(self):
        # Initialize all factors
        self.factors = [
            SastSemgrepFactor(),
            VirusTotalConsensusFactor(),
            EntropyObfuscationFactor(),
            ManifestSecurityFactor(),
            NetworkBehaviorLiteFactor(),
            WebstoreReputationBehaviorFactor(),
            ChromeStatsBehaviorFactor(),
        ]
    
    def build(self, signal_pack: SignalPack) -> SecurityScorecard:
        """
        Build a complete security scorecard from a signal pack.
        
        Args:
            signal_pack: SignalPack from Layer 0
            
        Returns:
            SecurityScorecard with all factor results
        """
        logger.info("Building security scorecard for scan_id=%s", signal_pack.scan_id)
        
        scorecard = SecurityScorecard(scan_id=signal_pack.scan_id)
        
        total_points = 0.0
        max_points = 0.0
        weighted_confidence = 0.0
        
        # Evaluate all factors
        for factor in self.factors:
            try:
                result = factor.evaluate(signal_pack)
                scorecard.factors[result.factor_id] = result
                
                total_points += result.points
                max_points += result.max_points
                weighted_confidence += result.confidence * result.max_points
                
                logger.debug(
                    "Factor %s: %.1f/%.1f points (%.0f%% confidence)",
                    result.factor_id,
                    result.points,
                    result.max_points,
                    result.confidence * 100,
                )
                
            except Exception as e:
                logger.error("Error evaluating factor %s: %s", factor.FACTOR_ID, e)
                # Add empty result on error
                scorecard.factors[factor.FACTOR_ID] = FactorResult(
                    factor_id=factor.FACTOR_ID,
                    points=0.0,
                    max_points=factor.MAX_POINTS,
                    confidence=0.0,
                    details={"error": str(e)},
                )
                max_points += factor.MAX_POINTS
        
        scorecard.total_points = total_points
        scorecard.max_possible_points = max_points
        
        # Calculate overall confidence as weighted average
        if max_points > 0:
            scorecard.overall_confidence = weighted_confidence / max_points
        
        logger.info(
            "Scorecard built: score=%d, risk=%s, points=%.1f/%.1f",
            scorecard.security_score,
            scorecard.risk_level,
            scorecard.total_points,
            scorecard.max_possible_points,
        )
        
        return scorecard

