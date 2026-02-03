"""
Golden Snapshot Tests for ExtensionShield

This test suite ensures that refactors don't silently change scores, verdicts,
or evidence items without notice. It validates:
- Score stays in [0,100]
- Verdict remains identical
- Top 3 evidence items remain stable (or intentionally changed)

These are "golden snapshot" tests - they compare current results against
known-good baseline snapshots. If a test fails, it means either:
1. A bug was introduced (fix it)
2. An intentional change was made (update the snapshot)
"""

import json
import pytest
from pathlib import Path
from typing import Dict, Any, List, Optional

# Path to fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_scan_result(fixture_path: Path) -> Dict[str, Any]:
    """Load a scan result from a fixture file."""
    with open(fixture_path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_score(result: Dict[str, Any]) -> Optional[int]:
    """Extract the overall security score from a scan result."""
    return result.get("overall_security_score")


def extract_verdict(result: Dict[str, Any]) -> Optional[str]:
    """Extract the governance verdict from a scan result."""
    # Try multiple possible locations for verdict
    verdict = result.get("governance_verdict")
    if verdict:
        return verdict
    
    # Try governance_bundle.decision.verdict
    decision = result.get("governance_bundle", {}).get("decision", {})
    if decision:
        return decision.get("verdict")
    
    # Try governance_report.decision.verdict
    report = result.get("governance_report", {}).get("decision", {})
    if report:
        return report.get("verdict")
    
    return None


def extract_top_evidence_items(result: Dict[str, Any], top_n: int = 3) -> List[Dict[str, Any]]:
    """
    Extract the top N evidence items from a scan result.
    
    Evidence items are sorted by evidence_id (ev_001, ev_002, etc.) for stable ordering.
    Returns a list of evidence item dictionaries with stable keys for comparison.
    """
    evidence_index = result.get("governance_bundle", {}).get("evidence_index", {})
    evidence_dict = evidence_index.get("evidence", {})
    
    if not evidence_dict:
        return []
    
    # Sort by evidence_id for stable ordering
    sorted_evidence_ids = sorted(evidence_dict.keys())
    top_evidence_ids = sorted_evidence_ids[:top_n]
    
    # Extract stable fields for comparison
    evidence_items = []
    for ev_id in top_evidence_ids:
        ev_item = evidence_dict[ev_id]
        # Create a stable representation for comparison
        stable_item = {
            "evidence_id": ev_item.get("evidence_id"),
            "file_path": ev_item.get("file_path"),
            "provenance": ev_item.get("provenance"),
            # Include file_hash for reproducibility
            "file_hash": ev_item.get("file_hash"),
        }
        # Optionally include line numbers if present
        if ev_item.get("line_start") is not None:
            stable_item["line_start"] = ev_item.get("line_start")
        if ev_item.get("line_end") is not None:
            stable_item["line_end"] = ev_item.get("line_end")
        
        evidence_items.append(stable_item)
    
    return evidence_items


def get_all_fixtures() -> List[Path]:
    """Get all fixture files from the fixtures directory."""
    if not FIXTURES_DIR.exists():
        pytest.skip(f"Fixtures directory not found: {FIXTURES_DIR}")
    
    fixture_files = list(FIXTURES_DIR.glob("*_results.json"))
    if not fixture_files:
        pytest.skip(f"No fixture files found in {FIXTURES_DIR}")
    
    return sorted(fixture_files)


# Golden snapshots - these are the baseline values
# Update these when making intentional changes to scoring/verdict logic
# To regenerate: python3 tests/generate_snapshots.py
GOLDEN_SNAPSHOTS = {
    "abikfbojmghmfjdjlbagiamkinbmbaic_results.json": {
        "score": 85,
        "verdict": "BLOCK",
        "top_3_evidence": [],
    },
    "edacconmaakjimmfgnblocblbcdcpbko_results.json": {
        "score": 92,
        "verdict": "NEEDS_REVIEW",
        "top_3_evidence": [
            {
                "evidence_id": "ev_001",
                "file_hash": "sha256:path_74d0f442028ea192",
                "file_path": "background.bundle.js",
                "provenance": "Entropy: byte_entropy=5.16, char_entropy=5.16 - Patterns: function_constructor, unicode_escapes, base64_blob",
            },
            {
                "evidence_id": "ev_002",
                "file_hash": "sha256:path_829fb06591016275",
                "file_path": "main.bundle.js",
                "provenance": "Entropy: byte_entropy=5.27, char_entropy=5.27 - Patterns: function_constructor, hex_strings, unicode_escapes",
            },
        ],
    },
    "jnkmfdileelhofjcijamephohjechhna_results.json": {
        "score": 80,
        "verdict": "BLOCK",
        "top_3_evidence": [
            {
                "evidence_id": "ev_001",
                "file_hash": "sha256:path_ffa5b716b5a57837",
                "file_path": "manifest.json",
                "provenance": "Permission: tabs - The 'tabs' permission is not justified for the Google Analytics Debugger extension because its primary function is to print debug information to the JavaScript console for Google Analytics. Access to tab URLs, titles, and favicon URLs is not necessary for this functionality.",
            },
            {
                "evidence_id": "ev_002",
                "file_hash": "sha256:path_ffa5b716b5a57837",
                "file_path": "manifest.json",
                "provenance": "Permission: declarativeNetRequest - The Google Analytics Debugger extension is designed to provide detailed information about Google Analytics requests by enabling the debug version of the JavaScript. The declarativeNetRequest permission could be justified if the extension needs to modify or inspect network requests to provide accurate debugging information. However, the description does not explicitly state the need to block, redirect, or modify requests, which are the primary capabilities of this permission. Without clear evidence that these capabilities are necessary for its core functionality, the permission request may not be fully justified.",
            },
            {
                "evidence_id": "ev_003",
                "file_hash": "sha256:path_ffa5b716b5a57837",
                "file_path": "manifest.json",
                "provenance": "Manifest: Broad host access patterns detected",
            },
        ],
    },
    "nkabooldphfdjcbhcodblkfmigmpchhi_results.json": {
        "score": 86,
        "verdict": "NEEDS_REVIEW",
        "top_3_evidence": [
            {
                "evidence_id": "ev_001",
                "file_hash": "sha256:path_bb06783fccd762e4",
                "file_path": "background.js",
                "line_start": 13,
                "line_end": 13,
                "provenance": "SAST: src.extension_shield.config.test.import_scripts [INFO]",
            },
            {
                "evidence_id": "ev_002",
                "file_hash": "sha256:path_ffa5b716b5a57837",
                "file_path": "manifest.json",
                "provenance": "Permission: tabs - The 'tabs' permission is not justified for the described functionality of saving screenshots and images to Pinterest. Access to tab URLs, titles, and favicon URLs is not necessary for capturing screenshots or listing images on a page. Monitoring tab creation/closure and tracking tab navigation also exceed the stated purpose of the extension.",
            },
            {
                "evidence_id": "ev_003",
                "file_hash": "sha256:path_ffa5b716b5a57837",
                "file_path": "manifest.json",
                "provenance": "Permission: cookies - The permission to read, modify, and delete cookies is not justified for the functionality described. Saving screenshots and images to Pinterest, visually searching pins, and listing pinnable images do not inherently require access to cookies, which are typically used for session management and user tracking.",
            },
        ],
    },
    "nobaaibkcalggmjnjhnlmmcldllpogjp_results.json": {
        "score": 90,
        "verdict": "NEEDS_REVIEW",
        "top_3_evidence": [],
    },
}


def generate_snapshots_from_fixtures():
    """
    Helper function to generate golden snapshots from current fixtures.
    This is useful when first creating the test or when updating snapshots.
    """
    snapshots = {}
    for fixture_path in get_all_fixtures():
        result = load_scan_result(fixture_path)
        score = extract_score(result)
        verdict = extract_verdict(result)
        top_evidence = extract_top_evidence_items(result, top_n=3)
        
        snapshots[fixture_path.name] = {
            "score": score,
            "verdict": verdict,
            "top_3_evidence": top_evidence,
        }
    
    return snapshots


@pytest.mark.parametrize("fixture_path", get_all_fixtures())
def test_score_in_range(fixture_path: Path):
    """Test that security score is always in the valid range [0, 100]."""
    result = load_scan_result(fixture_path)
    score = extract_score(result)
    
    if score is not None:
        assert 0 <= score <= 100, (
            f"Score {score} is out of valid range [0, 100] "
            f"for fixture {fixture_path.name}"
        )


@pytest.mark.parametrize("fixture_path", get_all_fixtures())
def test_verdict_unchanged(fixture_path: Path):
    """Test that governance verdict matches the golden snapshot."""
    result = load_scan_result(fixture_path)
    current_verdict = extract_verdict(result)
    fixture_name = fixture_path.name
    
    # Get golden snapshot
    golden = GOLDEN_SNAPSHOTS.get(fixture_name, {})
    golden_verdict = golden.get("verdict")
    
    # If no golden snapshot exists, use current value as baseline
    if golden_verdict is None:
        # First run - store current value
        pytest.skip(
            f"No golden snapshot for verdict in {fixture_name}. "
            f"Current value: {current_verdict}. "
            f"Update GOLDEN_SNAPSHOTS to set baseline."
        )
    
    assert current_verdict == golden_verdict, (
        f"Verdict changed for {fixture_name}:\n"
        f"  Expected (golden): {golden_verdict}\n"
        f"  Actual (current):  {current_verdict}\n"
        f"If this is intentional, update GOLDEN_SNAPSHOTS."
    )


@pytest.mark.parametrize("fixture_path", get_all_fixtures())
def test_score_unchanged(fixture_path: Path):
    """Test that security score matches the golden snapshot."""
    result = load_scan_result(fixture_path)
    current_score = extract_score(result)
    fixture_name = fixture_path.name
    
    # Get golden snapshot
    golden = GOLDEN_SNAPSHOTS.get(fixture_name, {})
    golden_score = golden.get("score")
    
    # If no golden snapshot exists, use current value as baseline
    if golden_score is None:
        pytest.skip(
            f"No golden snapshot for score in {fixture_name}. "
            f"Current value: {current_score}. "
            f"Update GOLDEN_SNAPSHOTS to set baseline."
        )
    
    assert current_score == golden_score, (
        f"Score changed for {fixture_name}:\n"
        f"  Expected (golden): {golden_score}\n"
        f"  Actual (current):  {current_score}\n"
        f"If this is intentional, update GOLDEN_SNAPSHOTS."
    )


@pytest.mark.parametrize("fixture_path", get_all_fixtures())
def test_top_evidence_unchanged(fixture_path: Path):
    """Test that top 3 evidence items match the golden snapshot."""
    result = load_scan_result(fixture_path)
    current_evidence = extract_top_evidence_items(result, top_n=3)
    fixture_name = fixture_path.name
    
    # Get golden snapshot
    golden = GOLDEN_SNAPSHOTS.get(fixture_name, {})
    golden_evidence = golden.get("top_3_evidence")
    
    # If no golden snapshot exists, use current value as baseline
    if golden_evidence is None:
        pytest.skip(
            f"No golden snapshot for evidence in {fixture_name}. "
            f"Current top 3 evidence items: {current_evidence}. "
            f"Update GOLDEN_SNAPSHOTS to set baseline."
        )
    
    assert current_evidence == golden_evidence, (
        f"Top 3 evidence items changed for {fixture_name}:\n"
        f"  Expected (golden): {golden_evidence}\n"
        f"  Actual (current):  {current_evidence}\n"
        f"If this is intentional, update GOLDEN_SNAPSHOTS."
    )


def test_all_fixtures_have_snapshots():
    """Test that all fixtures have corresponding golden snapshots."""
    fixtures = get_all_fixtures()
    fixture_names = {f.name for f in fixtures}
    snapshot_names = set(GOLDEN_SNAPSHOTS.keys())
    
    missing = fixture_names - snapshot_names
    if missing:
        pytest.fail(
            f"Fixtures without golden snapshots: {sorted(missing)}\n"
            f"Add entries to GOLDEN_SNAPSHOTS or use generate_snapshots_from_fixtures() "
            f"to generate them."
        )
    
    extra = snapshot_names - fixture_names
    if extra:
        pytest.fail(
            f"Golden snapshots without corresponding fixtures: {sorted(extra)}\n"
            f"Remove entries from GOLDEN_SNAPSHOTS."
        )


# Utility function to help generate snapshots (can be run manually)
if __name__ == "__main__":
    """Run this script to generate golden snapshots from current fixtures."""
    import pprint
    
    print("Generating golden snapshots from fixtures...")
    snapshots = generate_snapshots_from_fixtures()
    
    print("\n# Generated Golden Snapshots")
    print("# Copy this into GOLDEN_SNAPSHOTS in test_golden_snapshots.py\n")
    print("GOLDEN_SNAPSHOTS = {")
    for name, data in sorted(snapshots.items()):
        print(f'    "{name}": {{')
        print(f'        "score": {data["score"]},')
        print(f'        "verdict": {repr(data["verdict"])},')
        print(f'        "top_3_evidence": {pprint.pformat(data["top_3_evidence"], indent=12)},')
        print("    },")
    print("}")

