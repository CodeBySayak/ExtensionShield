"""
Test Utilities for Scoring Module

Provides helper functions to create valid SignalPack instances and related
test data without encountering model validation errors.

Usage:
    from tests.scoring.utils import (
        make_min_signal_pack,
        add_sast_findings,
        make_risky_signal_pack,
        make_malware_signal_pack,
    )
    
    # Minimal valid signal pack
    pack = make_min_signal_pack()
    
    # Add SAST findings
    add_sast_findings(pack, n=3, severity="HIGH")
    
    # Pre-built risky pack
    risky = make_risky_signal_pack()
"""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from extension_shield.governance.signal_pack import (
    SignalPack,
    SastSignalPack,
    SastFindingNormalized,
    VirusTotalSignalPack,
    EntropySignalPack,
    WebstoreStatsSignalPack,
    WebstoreReviewsSignalPack,
    PermissionsSignalPack,
    ChromeStatsSignalPack,
    NetworkSignalPack,
)


def make_min_signal_pack(
    scan_id: str = "test-scan",
    extension_id: Optional[str] = "test-extension-id",
) -> SignalPack:
    """
    Create a minimal valid SignalPack with all defaults.
    
    This pack has:
    - All sub-packs initialized to empty/default states
    - Network disabled with confidence=0.0
    - No findings, no evidence
    
    Args:
        scan_id: Unique scan identifier
        extension_id: Optional extension ID
        
    Returns:
        SignalPack with all fields properly initialized
    """
    return SignalPack(
        scan_id=scan_id,
        extension_id=extension_id,
        sast=SastSignalPack(),
        virustotal=VirusTotalSignalPack(),
        entropy=EntropySignalPack(),
        webstore_stats=WebstoreStatsSignalPack(),
        webstore_reviews=WebstoreReviewsSignalPack(),
        permissions=PermissionsSignalPack(),
        chromestats=ChromeStatsSignalPack(),
        network=NetworkSignalPack(enabled=False, confidence=0.0),
        evidence=[],
        created_at=datetime.now(timezone.utc),
    )


def make_sast_finding(
    check_id: str = "test-rule",
    file_path: str = "src/background.js",
    line_number: Optional[int] = 1,
    severity: str = "MEDIUM",
    message: str = "Test finding",
    category: Optional[str] = None,
    code_snippet: Optional[str] = None,
) -> SastFindingNormalized:
    """
    Create a single SAST finding with real field names.
    
    SastFindingNormalized fields:
    - check_id: str (REQUIRED)
    - file_path: str (REQUIRED)
    - line_number: Optional[int] = None
    - severity: str = "INFO"
    - message: str = ""
    - category: Optional[str] = None
    - code_snippet: Optional[str] = None
    
    Args:
        check_id: Rule/check identifier
        file_path: Path to the file with finding
        line_number: Line number of finding
        severity: Severity level (CRITICAL, HIGH, MEDIUM, WARNING, INFO)
        message: Human-readable message
        category: Optional category
        code_snippet: Optional code snippet
        
    Returns:
        SastFindingNormalized instance
    """
    return SastFindingNormalized(
        check_id=check_id,
        file_path=file_path,
        line_number=line_number,
        severity=severity,
        message=message,
        category=category,
        code_snippet=code_snippet,
    )


def add_sast_findings(
    pack: SignalPack,
    n: int = 1,
    severity: str = "MEDIUM",
    base_check_id: str = "test-rule",
) -> SignalPack:
    """
    Add n SAST findings to a SignalPack.
    
    Modifies the pack in-place and returns it for chaining.
    
    Args:
        pack: SignalPack to modify
        n: Number of findings to add
        severity: Severity for all findings
        base_check_id: Base check ID (will be suffixed with index)
        
    Returns:
        The modified SignalPack
    """
    findings = []
    for i in range(n):
        findings.append(SastFindingNormalized(
            check_id=f"{base_check_id}-{i+1}",
            file_path=f"src/file_{i+1}.js",
            line_number=i * 10 + 1,
            severity=severity,
            message=f"Finding {i+1} with severity {severity}",
        ))
    
    # Update sast pack
    pack.sast = SastSignalPack(
        deduped_findings=pack.sast.deduped_findings + findings,
        files_scanned=pack.sast.files_scanned + n,
        confidence=0.9,
    )
    
    return pack


def add_vt_detections(
    pack: SignalPack,
    malicious_count: int = 0,
    suspicious_count: int = 0,
    total_engines: int = 70,
    malware_families: Optional[List[str]] = None,
) -> SignalPack:
    """
    Set VirusTotal detections on a SignalPack.
    
    Args:
        pack: SignalPack to modify
        malicious_count: Number of malicious detections
        suspicious_count: Number of suspicious detections
        total_engines: Total AV engines
        malware_families: Optional list of malware family names
        
    Returns:
        The modified SignalPack
    """
    pack.virustotal = VirusTotalSignalPack(
        enabled=True,
        malicious_count=malicious_count,
        suspicious_count=suspicious_count,
        total_engines=total_engines,
        malware_families=malware_families or [],
        threat_level="malware" if malicious_count >= 5 else (
            "suspicious" if malicious_count > 0 else "clean"
        ),
    )
    return pack


def add_permissions(
    pack: SignalPack,
    api_permissions: Optional[List[str]] = None,
    host_permissions: Optional[List[str]] = None,
    has_broad_host_access: bool = False,
) -> SignalPack:
    """
    Set permissions on a SignalPack.
    
    Args:
        pack: SignalPack to modify
        api_permissions: List of API permissions
        host_permissions: List of host permissions
        has_broad_host_access: Whether extension has <all_urls> or similar
        
    Returns:
        The modified SignalPack
    """
    api_perms = api_permissions or []
    host_perms = host_permissions or []
    
    pack.permissions = PermissionsSignalPack(
        api_permissions=api_perms,
        host_permissions=host_perms,
        has_broad_host_access=has_broad_host_access,
        total_permissions=len(api_perms) + len(host_perms),
    )
    return pack


def add_webstore_stats(
    pack: SignalPack,
    installs: Optional[int] = None,
    rating_avg: Optional[float] = None,
    rating_count: Optional[int] = None,
    has_privacy_policy: bool = True,
    last_updated: Optional[str] = None,
) -> SignalPack:
    """
    Set webstore stats on a SignalPack.
    
    Args:
        pack: SignalPack to modify
        installs: User install count
        rating_avg: Average rating (0-5)
        rating_count: Number of ratings
        has_privacy_policy: Whether privacy policy exists
        last_updated: Last update date string
        
    Returns:
        The modified SignalPack
    """
    pack.webstore_stats = WebstoreStatsSignalPack(
        installs=installs,
        rating_avg=rating_avg,
        rating_count=rating_count,
        has_privacy_policy=has_privacy_policy,
        last_updated=last_updated,
    )
    return pack


def add_network_analysis(
    pack: SignalPack,
    domains: Optional[List[str]] = None,
    has_runtime_url_construction: bool = False,
    suspicious_flags: Optional[Dict[str, bool]] = None,
    confidence: float = 0.7,
) -> SignalPack:
    """
    Set network analysis on a SignalPack.
    
    Args:
        pack: SignalPack to modify
        domains: List of external domains
        has_runtime_url_construction: Dynamic URL building detected
        suspicious_flags: Dict of suspicious pattern flags
        confidence: Confidence in the analysis
        
    Returns:
        The modified SignalPack
    """
    pack.network = NetworkSignalPack(
        enabled=True,
        domains=domains or [],
        has_runtime_url_construction=has_runtime_url_construction,
        suspicious_flags=suspicious_flags or {},
        confidence=confidence,
    )
    return pack


# =============================================================================
# PRE-BUILT SIGNAL PACKS FOR COMMON TEST SCENARIOS
# =============================================================================


def make_clean_signal_pack(
    scan_id: str = "clean-test",
    installs: int = 100000,
) -> SignalPack:
    """
    Create a clean extension signal pack (should score high, ALLOW).
    
    Characteristics:
    - No SAST findings
    - VT clean
    - Good webstore stats
    - Minimal permissions
    """
    pack = make_min_signal_pack(scan_id=scan_id)
    add_vt_detections(pack, malicious_count=0, total_engines=70)
    add_permissions(pack, api_permissions=["storage"])
    add_webstore_stats(
        pack,
        installs=installs,
        rating_avg=4.5,
        rating_count=1000,
        has_privacy_policy=True,
    )
    return pack


def make_risky_signal_pack(
    scan_id: str = "risky-test",
) -> SignalPack:
    """
    Create a risky extension signal pack (should score low, NEEDS_REVIEW).
    
    Characteristics:
    - Multiple HIGH severity SAST findings
    - VT with 1-2 suspicious detections (WARN, not BLOCK)
    - Broad permissions
    - Low webstore stats
    """
    pack = make_min_signal_pack(scan_id=scan_id)
    add_sast_findings(pack, n=3, severity="HIGH")
    add_vt_detections(pack, malicious_count=2, suspicious_count=1)
    add_permissions(
        pack,
        api_permissions=["cookies", "webRequest", "tabs", "storage"],
        has_broad_host_access=True,
    )
    add_webstore_stats(
        pack,
        installs=500,
        rating_avg=3.0,
        has_privacy_policy=False,
    )
    return pack


def make_malware_signal_pack(
    scan_id: str = "malware-test",
    malicious_count: int = 10,
) -> SignalPack:
    """
    Create a malware extension signal pack (should BLOCK via VT_MALWARE gate).
    
    Characteristics:
    - VT detections >= 5 (triggers BLOCK)
    - Known malware families
    """
    pack = make_min_signal_pack(scan_id=scan_id)
    add_vt_detections(
        pack,
        malicious_count=malicious_count,
        malware_families=["Trojan.BrowserHijack", "Adware.Generic"],
    )
    add_webstore_stats(pack, installs=50)
    return pack


def make_critical_sast_signal_pack(
    scan_id: str = "critical-sast-test",
) -> SignalPack:
    """
    Create a signal pack with CRITICAL SAST findings (should BLOCK via CRITICAL_SAST gate).
    """
    pack = make_min_signal_pack(scan_id=scan_id)
    
    # Add CRITICAL findings directly
    pack.sast = SastSignalPack(
        deduped_findings=[
            SastFindingNormalized(
                check_id="sql-injection",
                file_path="db.js",
                severity="CRITICAL",
                message="SQL injection vulnerability",
            ),
        ],
        files_scanned=10,
        confidence=0.95,
    )
    
    add_vt_detections(pack, malicious_count=0)
    add_webstore_stats(pack, installs=1000, has_privacy_policy=True)
    
    return pack


def make_test_manifest(
    name: str = "Test Extension",
    description: str = "A test extension",
    manifest_version: int = 3,
) -> Dict[str, Any]:
    """
    Create a minimal manifest for testing.
    
    Args:
        name: Extension name
        description: Extension description
        manifest_version: Manifest version (2 or 3)
        
    Returns:
        Manifest dictionary
    """
    return {
        "name": name,
        "description": description,
        "manifest_version": manifest_version,
        "version": "1.0.0",
    }

