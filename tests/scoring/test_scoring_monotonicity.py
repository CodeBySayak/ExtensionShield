"""
Scoring Monotonicity Tests

Verifies that the scoring engine maintains monotonicity:
- Adding risk factors should decrease (or not increase) scores
- Never should adding risk improve scores

Uses test utilities from tests/scoring/utils.py to construct valid SignalPacks.
"""

import pytest
import sys
from pathlib import Path

# Add tests directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scoring.utils import (
    make_min_signal_pack,
    make_sast_finding,
    add_sast_findings,
    add_vt_detections,
    add_webstore_stats,
    make_test_manifest,
)
from extension_shield.scoring.engine import ScoringEngine
from extension_shield.scoring.models import Decision
from extension_shield.governance.signal_pack import (
    SastSignalPack,
    SastFindingNormalized,
    PermissionsSignalPack,
    VirusTotalSignalPack,
)


class TestScoringMonotonicity:
    """Test that adding risk factors monotonically decreases scores."""
    
    @pytest.fixture
    def engine(self):
        """Create a scoring engine instance."""
        return ScoringEngine(weights_version="v1")
    
    @pytest.fixture
    def manifest(self):
        """Create a test manifest."""
        return make_test_manifest()
    
    def test_adding_critical_sast_decreases_security_score(self, engine, manifest):
        """
        Test: Adding a CRITICAL SAST finding should decrease (or not increase)
        the security_score.
        """
        # Baseline: clean pack with no findings
        pack_clean = make_min_signal_pack(scan_id="sast-clean")
        add_webstore_stats(pack_clean, installs=10000)
        
        result_clean = engine.calculate_scores(pack_clean, manifest)
        
        # Add one CRITICAL SAST finding
        pack_with_critical = make_min_signal_pack(scan_id="sast-critical")
        pack_with_critical.sast = SastSignalPack(
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
        add_webstore_stats(pack_with_critical, installs=10000)
        
        result_with_critical = engine.calculate_scores(pack_with_critical, manifest)
        
        print(f"\nClean: security={result_clean.security_score}")
        print(f"With CRITICAL: security={result_with_critical.security_score}")
        
        # Monotonicity: adding risk should not increase score
        assert result_with_critical.security_score <= result_clean.security_score, (
            f"Adding CRITICAL finding should not increase security_score: "
            f"{result_with_critical.security_score} > {result_clean.security_score}"
        )
    
    def test_adding_multiple_sast_monotonically_decreases(self, engine, manifest):
        """
        Test: Adding more SAST findings should monotonically decrease scores.
        
        0 findings >= 1 finding >= 3 findings >= 10 findings
        """
        scores = []
        
        for n in [0, 1, 3, 10]:
            pack = make_min_signal_pack(scan_id=f"sast-{n}")
            if n > 0:
                add_sast_findings(pack, n=n, severity="HIGH")
            add_webstore_stats(pack, installs=5000)
            
            result = engine.calculate_scores(pack, manifest, user_count=5000)
            scores.append((n, result.security_score))
            print(f"  {n} findings: security={result.security_score}")
        
        # Verify monotonicity
        for i in range(len(scores) - 1):
            n1, score1 = scores[i]
            n2, score2 = scores[i + 1]
            assert score2 <= score1, (
                f"Score should decrease with more findings: "
                f"{n1} findings ({score1}) to {n2} findings ({score2})"
            )
        
        print("  ✓ Monotonically decreasing")
    
    def test_adding_high_risk_permission_decreases_privacy_score(self, engine, manifest):
        """
        Test: Adding high-risk permissions should decrease privacy_score.
        
        normalize_permissions_baseline uses:
        - perms.high_risk_permissions (list)
        - perms.unreasonable_permissions (list)
        """
        # Baseline: minimal permissions
        pack_minimal = make_min_signal_pack(scan_id="perms-minimal")
        pack_minimal.permissions = PermissionsSignalPack(
            api_permissions=["storage"],
            high_risk_permissions=[],
            unreasonable_permissions=[],
            total_permissions=1,
        )
        add_webstore_stats(pack_minimal, installs=10000)
        
        result_minimal = engine.calculate_scores(pack_minimal, manifest)
        
        # Add high-risk permissions
        pack_risky = make_min_signal_pack(scan_id="perms-risky")
        pack_risky.permissions = PermissionsSignalPack(
            api_permissions=["storage", "cookies", "webRequest", "history"],
            high_risk_permissions=["cookies", "webRequest", "history"],
            unreasonable_permissions=[],
            has_broad_host_access=True,
            total_permissions=4,
        )
        add_webstore_stats(pack_risky, installs=10000)
        
        result_risky = engine.calculate_scores(pack_risky, manifest)
        
        print(f"\nMinimal perms: privacy={result_minimal.privacy_score}")
        print(f"Risky perms: privacy={result_risky.privacy_score}")
        
        # Monotonicity: adding risk should not increase score
        assert result_risky.privacy_score <= result_minimal.privacy_score, (
            f"Adding high-risk permissions should not increase privacy_score: "
            f"{result_risky.privacy_score} > {result_minimal.privacy_score}"
        )
    
    def test_adding_unreasonable_permissions_decreases_privacy_score(self, engine, manifest):
        """
        Test: Adding unreasonable permissions should decrease privacy_score.
        """
        # Baseline: no unreasonable permissions
        pack_reasonable = make_min_signal_pack(scan_id="perms-reasonable")
        pack_reasonable.permissions = PermissionsSignalPack(
            api_permissions=["storage", "tabs"],
            high_risk_permissions=[],
            unreasonable_permissions=[],
            total_permissions=2,
        )
        add_webstore_stats(pack_reasonable, installs=10000)
        
        result_reasonable = engine.calculate_scores(pack_reasonable, manifest)
        
        # Add unreasonable permissions
        pack_unreasonable = make_min_signal_pack(scan_id="perms-unreasonable")
        pack_unreasonable.permissions = PermissionsSignalPack(
            api_permissions=["storage", "tabs", "debugger", "proxy"],
            high_risk_permissions=[],
            unreasonable_permissions=["debugger", "proxy"],
            total_permissions=4,
        )
        add_webstore_stats(pack_unreasonable, installs=10000)
        
        result_unreasonable = engine.calculate_scores(pack_unreasonable, manifest)
        
        print(f"\nReasonable: privacy={result_reasonable.privacy_score}")
        print(f"Unreasonable: privacy={result_unreasonable.privacy_score}")
        
        # Monotonicity: adding risk should not increase score
        assert result_unreasonable.privacy_score <= result_reasonable.privacy_score, (
            f"Adding unreasonable permissions should not increase privacy_score: "
            f"{result_unreasonable.privacy_score} > {result_reasonable.privacy_score}"
        )


class TestVTGateBehavior:
    """Test VirusTotal gate behavior at different detection thresholds."""
    
    @pytest.fixture
    def engine(self):
        """Create a scoring engine instance."""
        return ScoringEngine(weights_version="v1")
    
    @pytest.fixture
    def manifest(self):
        """Create a test manifest."""
        return make_test_manifest()
    
    def test_vt_malicious_1_triggers_warn(self, engine, manifest):
        """
        Test: malicious_count=1 should trigger WARN (not BLOCK).
        
        Per Phase 1 fixups: 1-4 detections = WARN
        """
        pack_warn = make_min_signal_pack(scan_id="vt-warn-1")
        pack_warn.virustotal = VirusTotalSignalPack(
            enabled=True,
            malicious_count=1,
            suspicious_count=0,
            total_engines=70,
        )
        add_webstore_stats(pack_warn, installs=10000)
        
        result = engine.calculate_scores(pack_warn, manifest)
        gate_results = engine.get_gate_results()
        vt_gate = next((g for g in gate_results if g.gate_id == "VT_MALWARE"), None)
        
        print(f"\nVT 1 detection: decision={result.decision.value}")
        print(f"VT gate: decision={vt_gate.decision if vt_gate else 'N/A'}, "
              f"triggered={vt_gate.triggered if vt_gate else 'N/A'}")
        
        assert vt_gate is not None, "VT_MALWARE gate should exist"
        assert vt_gate.triggered, "VT_MALWARE gate should trigger at 1 detection"
        assert vt_gate.decision == "WARN", (
            f"VT_MALWARE should WARN at 1 detection, got {vt_gate.decision}"
        )
    
    def test_vt_malicious_4_triggers_warn(self, engine, manifest):
        """
        Test: malicious_count=4 should still be WARN (not BLOCK).
        """
        pack_warn = make_min_signal_pack(scan_id="vt-warn-4")
        pack_warn.virustotal = VirusTotalSignalPack(
            enabled=True,
            malicious_count=4,
            suspicious_count=0,
            total_engines=70,
        )
        add_webstore_stats(pack_warn, installs=10000)
        
        result = engine.calculate_scores(pack_warn, manifest)
        gate_results = engine.get_gate_results()
        vt_gate = next((g for g in gate_results if g.gate_id == "VT_MALWARE"), None)
        
        print(f"\nVT 4 detections: decision={result.decision.value}")
        print(f"VT gate: decision={vt_gate.decision if vt_gate else 'N/A'}")
        
        assert vt_gate.decision == "WARN", (
            f"VT_MALWARE should WARN at 4 detections, got {vt_gate.decision}"
        )
    
    def test_vt_malicious_5_triggers_block(self, engine, manifest):
        """
        Test: malicious_count=5 should trigger BLOCK.
        
        Per Phase 1 fixups: >=5 detections = BLOCK
        """
        pack_dirty = make_min_signal_pack(scan_id="vt-block-5")
        pack_dirty.virustotal = VirusTotalSignalPack(
            enabled=True,
            malicious_count=5,
            suspicious_count=0,
            total_engines=70,
        )
        add_webstore_stats(pack_dirty, installs=10000)
        
        result = engine.calculate_scores(pack_dirty, manifest)
        gate_results = engine.get_gate_results()
        vt_gate = next((g for g in gate_results if g.gate_id == "VT_MALWARE"), None)
        
        print(f"\nVT 5 detections: decision={result.decision.value}")
        print(f"VT gate: decision={vt_gate.decision if vt_gate else 'N/A'}")
        print(f"Hard gates triggered: {result.hard_gates_triggered}")
        
        assert vt_gate is not None, "VT_MALWARE gate should exist"
        assert vt_gate.triggered, "VT_MALWARE gate should trigger at 5 detections"
        assert vt_gate.decision == "BLOCK", (
            f"VT_MALWARE should BLOCK at 5 detections, got {vt_gate.decision}"
        )
        assert result.decision == Decision.BLOCK, (
            f"Final decision should be BLOCK, got {result.decision.value}"
        )
        assert "VT_MALWARE" in result.hard_gates_triggered, (
            "VT_MALWARE should be in hard_gates_triggered"
        )
    
    def test_vt_malicious_10_triggers_block(self, engine, manifest):
        """
        Test: malicious_count=10 should definitely BLOCK.
        """
        pack_dirty = make_min_signal_pack(scan_id="vt-block-10")
        pack_dirty.virustotal = VirusTotalSignalPack(
            enabled=True,
            malicious_count=10,
            suspicious_count=0,
            total_engines=70,
            malware_families=["Trojan.Generic", "Adware.BrowserHijack"],
        )
        add_webstore_stats(pack_dirty, installs=100)
        
        result = engine.calculate_scores(pack_dirty, manifest)
        
        print(f"\nVT 10 detections: decision={result.decision.value}")
        print(f"Hard gates triggered: {result.hard_gates_triggered}")
        
        assert result.decision == Decision.BLOCK
        assert "VT_MALWARE" in result.hard_gates_triggered
    
    def test_vt_clean_does_not_trigger_gate(self, engine, manifest):
        """
        Test: malicious_count=0 should not trigger VT_MALWARE gate.
        """
        pack_clean = make_min_signal_pack(scan_id="vt-clean")
        pack_clean.virustotal = VirusTotalSignalPack(
            enabled=True,
            malicious_count=0,
            suspicious_count=0,
            total_engines=70,
        )
        add_webstore_stats(pack_clean, installs=10000)
        
        result = engine.calculate_scores(pack_clean, manifest)
        gate_results = engine.get_gate_results()
        vt_gate = next((g for g in gate_results if g.gate_id == "VT_MALWARE"), None)
        
        print(f"\nVT 0 detections: decision={result.decision.value}")
        print(f"VT gate triggered: {vt_gate.triggered if vt_gate else 'N/A'}")
        
        assert vt_gate is not None
        assert not vt_gate.triggered, "VT_MALWARE should not trigger at 0 detections"
        assert vt_gate.decision == "ALLOW", "VT_MALWARE should ALLOW at 0 detections"
    
    def test_vt_monotonicity(self, engine, manifest):
        """
        Test: VT detections should monotonically affect scores.
        
        0 >= 1 >= 2 >= 5 >= 10 (in terms of security score)
        """
        print("\nVT Monotonicity Test:")
        
        scores = []
        for malicious_count in [0, 1, 2, 5, 10]:
            pack = make_min_signal_pack(scan_id=f"vt-mono-{malicious_count}")
            pack.virustotal = VirusTotalSignalPack(
                enabled=True,
                malicious_count=malicious_count,
                total_engines=70,
            )
            add_webstore_stats(pack, installs=10000)
            
            result = engine.calculate_scores(pack, manifest)
            scores.append((malicious_count, result.security_score))
            print(f"  VT {malicious_count}: security={result.security_score}")
        
        # Verify monotonicity
        for i in range(len(scores) - 1):
            mc1, score1 = scores[i]
            mc2, score2 = scores[i + 1]
            assert score2 <= score1, (
                f"Security score should decrease with more VT detections: "
                f"{mc1} detections ({score1}) to {mc2} detections ({score2})"
            )
        
        print("  ✓ Monotonically decreasing")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

