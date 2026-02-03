"""
Helper script to generate golden snapshots from fixture files.
Run this to populate GOLDEN_SNAPSHOTS in test_golden_snapshots.py
"""

import json
import pprint
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_scan_result(fixture_path: Path):
    """Load a scan result from a fixture file."""
    with open(fixture_path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_score(result):
    """Extract the overall security score from a scan result."""
    return result.get("overall_security_score")


def extract_verdict(result):
    """Extract the governance verdict from a scan result."""
    verdict = result.get("governance_verdict")
    if verdict:
        return verdict
    
    decision = result.get("governance_bundle", {}).get("decision", {})
    if decision:
        return decision.get("verdict")
    
    report = result.get("governance_report", {}).get("decision", {})
    if report:
        return report.get("verdict")
    
    return None


def extract_top_evidence_items(result, top_n=3):
    """Extract the top N evidence items from a scan result."""
    evidence_index = result.get("governance_bundle", {}).get("evidence_index", {})
    evidence_dict = evidence_index.get("evidence", {})
    
    if not evidence_dict:
        return []
    
    sorted_evidence_ids = sorted(evidence_dict.keys())
    top_evidence_ids = sorted_evidence_ids[:top_n]
    
    evidence_items = []
    for ev_id in top_evidence_ids:
        ev_item = evidence_dict[ev_id]
        stable_item = {
            "evidence_id": ev_item.get("evidence_id"),
            "file_path": ev_item.get("file_path"),
            "provenance": ev_item.get("provenance"),
            "file_hash": ev_item.get("file_hash"),
        }
        if ev_item.get("line_start") is not None:
            stable_item["line_start"] = ev_item.get("line_start")
        if ev_item.get("line_end") is not None:
            stable_item["line_end"] = ev_item.get("line_end")
        
        evidence_items.append(stable_item)
    
    return evidence_items


def main():
    """Generate golden snapshots from fixtures."""
    if not FIXTURES_DIR.exists():
        print(f"Error: Fixtures directory not found: {FIXTURES_DIR}")
        return
    
    fixture_files = sorted(FIXTURES_DIR.glob("*_results.json"))
    if not fixture_files:
        print(f"Error: No fixture files found in {FIXTURES_DIR}")
        return
    
    print("Generating golden snapshots from fixtures...\n")
    snapshots = {}
    
    for fixture_path in fixture_files:
        result = load_scan_result(fixture_path)
        score = extract_score(result)
        verdict = extract_verdict(result)
        top_evidence = extract_top_evidence_items(result, top_n=3)
        
        snapshots[fixture_path.name] = {
            "score": score,
            "verdict": verdict,
            "top_3_evidence": top_evidence,
        }
        
        print(f"Processed: {fixture_path.name}")
        print(f"  Score: {score}")
        print(f"  Verdict: {verdict}")
        print(f"  Evidence items: {len(top_evidence)}")
        print()
    
    print("\n" + "=" * 80)
    print("# Generated Golden Snapshots")
    print("# Copy this into GOLDEN_SNAPSHOTS in test_golden_snapshots.py\n")
    print("GOLDEN_SNAPSHOTS = {")
    for name, data in sorted(snapshots.items()):
        print(f'    "{name}": {{')
        print(f'        "score": {data["score"]},')
        print(f'        "verdict": {repr(data["verdict"])},')
        print(f'        "top_3_evidence": {pprint.pformat(data["top_3_evidence"], indent=12)},')
        print("    },")
    print("}")


if __name__ == "__main__":
    main()

