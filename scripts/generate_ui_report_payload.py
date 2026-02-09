#!/usr/bin/env python3
"""
Generate UI-friendly report payloads from scan pipeline.

Creates normalized report_view_model objects for two test cases:
- ALL_WEBSITES: Extension with broad host access
- SINGLE_DOMAIN: Extension with limited domain access
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from extension_shield.governance.tool_adapters import SignalPackBuilder
from extension_shield.scoring.engine import ScoringEngine
from extension_shield.core.summary_generator import SummaryGenerator
from extension_shield.core.impact_analyzer import ImpactAnalyzer
from extension_shield.core.privacy_compliance_analyzer import PrivacyComplianceAnalyzer


def _map_score_label_from_risk_level(risk_level: str) -> str:
    """Map scoring RiskLevel ('low'|'medium'|'high'|'critical'|'none') to prompt label."""
    rl = (risk_level or "").lower()
    if rl in ("critical", "high"):
        return "HIGH RISK"
    if rl == "medium":
        return "MEDIUM RISK"
    return "LOW RISK"


def _summary_contradicts_label(text: str, score_label: str) -> bool:
    """Check if executive summary text contradicts the authoritative score_label."""
    t = (text or "").lower()
    if score_label == "LOW RISK":
        return any(x in t for x in ["high risk", "high-risk", "critical", "avoid", "severe"])
    if score_label == "HIGH RISK":
        return any(x in t for x in ["low risk", "low-risk", "safe", "no concerns", "no risk"])
    return False


def _fallback_executive_summary(score: int, score_label: str, host_scope_label: str) -> Dict[str, Any]:
    """
    Deterministic executive summary fallback (no LLM).

    IMPORTANT: The one_liner tone MUST match score_label.
    The dial and summary will never contradict each other when this
    function is the source of truth.
    """
    label_to_tone = {
        "LOW RISK": "Low risk overall",
        "MEDIUM RISK": "Some caution advised",
        "HIGH RISK": "High risk — avoid unless necessary",
    }
    one_liner = label_to_tone.get(score_label, "Risk level unavailable")
    one_liner += ". Review the notes below."

    what_to_watch: List[str] = []
    if host_scope_label == "ALL_WEBSITES":
        what_to_watch.append("Runs on all websites; avoid on sensitive accounts.")
    what_to_watch.append("Watch for updates that add new permissions or expand site access.")
    what_to_watch = what_to_watch[:2]

    why_this_score = [
        "Score is based on permissions, code signals, and store metadata.",
        "Capabilities indicate what it could do, not intent.",
        "Evidence links show exactly what triggered the score.",
    ]

    return {
        "one_liner": one_liner,
        "why_this_score": why_this_score,
        "what_to_watch": what_to_watch,
        "confidence": "MEDIUM",
        "score": int(score),
        "score_label": score_label,
        # Legacy-compat fields used elsewhere in the codebase
        "summary": one_liner,
        "key_findings": why_this_score,
        "recommendations": what_to_watch,
        "overall_risk_level": "unknown",
        "overall_security_score": int(score),
    }


def _bucket(risk_level: str, bullets: List[str], mitigations: List[str]) -> Dict[str, Any]:
    return {
        "risk_level": risk_level,
        "bullets": bullets[:3],
        "mitigations": mitigations[:3],
    }


def _fallback_impact_from_capability_flags(
    capability_flags: Dict[str, Any],
    external_domains: List[str],
    network_evidence: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Deterministic impact buckets (no LLM)."""
    flags = capability_flags or {}

    # ----------------------------
    # Data access
    # ----------------------------
    data_bullets: List[str] = []
    if flags.get("can_read_all_sites"):
        data_bullets.append("Can read or interact with pages across all websites.")
    elif flags.get("can_read_specific_sites"):
        data_bullets.append("Can read or interact with pages on specific websites.")
    if flags.get("can_read_tabs"):
        data_bullets.append("Can access open tab context (e.g., URLs/titles).")
    if flags.get("can_read_cookies"):
        data_bullets.append("Could access cookies for matching sites.")
    if flags.get("can_read_history"):
        data_bullets.append("Could access browsing history.")

    if flags.get("can_read_all_sites") or flags.get("can_read_history") or flags.get("can_read_cookies"):
        data_risk = "HIGH"
    elif flags.get("can_read_specific_sites") or flags.get("can_read_tabs"):
        data_risk = "MEDIUM"
    elif data_bullets:
        data_risk = "LOW"
    else:
        data_risk = "UNKNOWN"

    data_mitigations = [
        "Restrict site access to only the domains required.",
        "Use a separate browser profile for sensitive accounts.",
    ]

    # ----------------------------
    # Browser control
    # ----------------------------
    ctrl_bullets: List[str] = []
    if flags.get("can_inject_scripts"):
        ctrl_bullets.append("Can inject scripts into pages (content scripts / scripting).")
    if flags.get("can_modify_page_content"):
        ctrl_bullets.append("Can modify page content on matching sites.")
    if flags.get("can_block_or_modify_network"):
        ctrl_bullets.append("Can observe or modify network requests.")
    if flags.get("can_control_proxy"):
        ctrl_bullets.append("Can control proxy settings.")
    if flags.get("can_manage_extensions"):
        ctrl_bullets.append("Can manage other extensions.")
    if flags.get("can_debugger"):
        ctrl_bullets.append("Can use the debugger API.")

    if any(flags.get(k) for k in ["can_manage_extensions", "can_control_proxy", "can_debugger", "can_block_or_modify_network"]):
        ctrl_risk = "HIGH"
    elif any(flags.get(k) for k in ["can_inject_scripts", "can_modify_page_content"]):
        ctrl_risk = "MEDIUM"
    elif ctrl_bullets:
        ctrl_risk = "LOW"
    else:
        ctrl_risk = "UNKNOWN"

    ctrl_mitigations = [
        "Monitor for unexpected page changes or blocked requests.",
        "Limit use to non-sensitive workflows if possible.",
    ]

    # ----------------------------
    # External sharing (evidence-based)
    # ----------------------------
    if not external_domains and not network_evidence:
        ext_bucket = _bucket("UNKNOWN", [], [])
    else:
        ext_bullets: List[str] = []
        if external_domains:
            ext_bullets.append(f"Contacts external domains (examples: {', '.join(external_domains[:3])}).")
        if network_evidence:
            ext_bullets.append("Network-related code patterns were detected in scan evidence.")
        ext_mitigations = [
            "Review network endpoints and confirm they match the intended functionality.",
            "Ensure disclosures and controls exist for any data sent externally.",
        ]
        ext_bucket = _bucket("MEDIUM", ext_bullets, ext_mitigations)

    return {
        "data_access": _bucket(data_risk, data_bullets, data_mitigations),
        "browser_control": _bucket(ctrl_risk, ctrl_bullets, ctrl_mitigations),
        "external_sharing": ext_bucket,
    }


def create_test_fixture_all_websites() -> Dict[str, Any]:
    """Create test fixture for ALL_WEBSITES case."""
    manifest = {
        "manifest_version": 3,
        "name": "Test Extension - All Websites",
        "version": "1.0.0",
        "description": "A test extension with broad host access",
        "permissions": ["storage", "tabs"],
        "host_permissions": ["<all_urls>"],
        "content_scripts": [
            {
                "matches": ["*://*/*"],
                "js": ["content.js"],
                "run_at": "document_idle"
            }
        ]
    }
    
    analysis_results = {
        "permissions_analysis": {
            "permissions_details": {
                "storage": {
                    "is_reasonable": True,
                    "justification_reasoning": "Used for storing user preferences"
                },
                "tabs": {
                    "is_reasonable": True,
                    "justification_reasoning": "Required for core functionality"
                }
            },
            "host_permissions_analysis": "Broad host access detected: <all_urls>"
        },
        "javascript_analysis": {
            "sast_analysis": "[RISK: LOW] No critical security findings detected.",
            "sast_findings": {}
        },
        "webstore_analysis": {
            "risk_summary": "Low risk extension with stable reputation",
            "risk_level": "low"
        },
        "virustotal_analysis": {
            "enabled": False,
            "summary": {"threat_level": "clean"}
        },
        "entropy_analysis": {
            "summary": {"overall_risk": "normal"}
        }
    }
    
    metadata = {
        "title": "Test Extension - All Websites",
        "user_count": 10000,
        "rating": 4.5,
        "ratings_count": 500,
        "developer_name": "Test Developer",
        "privacy_policy": "https://example.com/privacy"
    }
    
    return {
        "manifest": manifest,
        "analysis_results": analysis_results,
        "metadata": metadata,
        "extension_id": "test_all_websites_abc123",
        "scan_id": "scan_all_websites_001"
    }


def create_test_fixture_single_domain() -> Dict[str, Any]:
    """Create test fixture for SINGLE_DOMAIN case."""
    manifest = {
        "manifest_version": 3,
        "name": "Test Extension - Single Domain",
        "version": "1.0.0",
        "description": "A test extension with limited domain access",
        "permissions": ["storage"],
        "host_permissions": [
            "https://example.com/*",
            "https://*.example.com/*"
        ]
    }
    
    analysis_results = {
        "permissions_analysis": {
            "permissions_details": {
                "storage": {
                    "is_reasonable": True,
                    "justification_reasoning": "Used for storing user preferences"
                }
            },
            "host_permissions_analysis": "Limited to example.com domain"
        },
        "javascript_analysis": {
            "sast_analysis": "[RISK: LOW] No critical security findings detected.",
            "sast_findings": {}
        },
        "webstore_analysis": {
            "risk_summary": "Low risk extension with stable reputation",
            "risk_level": "low"
        },
        "virustotal_analysis": {
            "enabled": False,
            "summary": {"threat_level": "clean"}
        },
        "entropy_analysis": {
            "summary": {"overall_risk": "normal"}
        }
    }
    
    metadata = {
        "title": "Test Extension - Single Domain",
        "user_count": 5000,
        "rating": 4.2,
        "ratings_count": 200,
        "developer_name": "Test Developer",
        "privacy_policy": "https://example.com/privacy"
    }
    
    return {
        "manifest": manifest,
        "analysis_results": analysis_results,
        "metadata": metadata,
        "extension_id": "test_single_domain_xyz789",
        "scan_id": "scan_single_domain_001"
    }


def build_report_view_model(
    fixture: Dict[str, Any],
    executive_summary: Dict[str, Any],
    impact_analysis: Dict[str, Any],
    privacy_compliance: Dict[str, Any],
    scoring_result: Any,
    signal_pack: Any,
    host_access_summary: Dict[str, Any],
    capability_flags: Dict[str, Any],
    external_domains: List[str],
    network_evidence: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Build normalized report_view_model from pipeline outputs."""
    
    manifest = fixture["manifest"]
    metadata = fixture.get("metadata", {})
    
    # Extract host scope label
    host_scope_label = host_access_summary.get("host_scope_label", "UNKNOWN")
    
    # Build meta
    meta = {
        "extension_id": fixture["extension_id"],
        "name": manifest.get("name") or metadata.get("title") or "Unknown Extension",
        "version": manifest.get("version", "1.0.0"),
        "scan_id": fixture["scan_id"],
        "scanned_at": datetime.now().isoformat(),
        "host_scope_label": host_scope_label
    }
    
    # Build scorecard
    score = scoring_result.overall_score if scoring_result else 0
    score_label = executive_summary.get("score_label", "UNKNOWN")
    confidence = executive_summary.get("confidence", "UNKNOWN")
    one_liner = executive_summary.get("one_liner") or executive_summary.get("summary", "")
    
    scorecard = {
        "score": score,
        "score_label": score_label,
        "confidence": confidence,
        "one_liner": one_liner
    }
    
    # Build highlights
    what_to_watch = executive_summary.get("what_to_watch") or executive_summary.get("recommendations", [])
    
    # Ensure ALL_WEBSITES mentions broad host access in what_to_watch
    if host_scope_label == "ALL_WEBSITES":
        has_broad_mention = any(
            "broad" in item.lower() or "all websites" in item.lower() or "all_urls" in item.lower()
            for item in what_to_watch
        )
        if not has_broad_mention and len(what_to_watch) < 2:
            what_to_watch.append("Extension has access to all websites, which requires careful review")
    
    highlights = {
        "why_this_score": executive_summary.get("why_this_score") or executive_summary.get("key_findings", []),
        "what_to_watch": what_to_watch
    }
    
    # Build impact_cards
    impact_cards = []
    for bucket_id in ["data_access", "browser_control", "external_sharing"]:
        bucket = impact_analysis.get(bucket_id, {})
        
        # Special handling for external_sharing: if no evidence, set to UNKNOWN with empty bullets
        if bucket_id == "external_sharing":
            if not external_domains and not network_evidence:
                impact_cards.append({
                    "id": bucket_id,
                    "risk_level": "UNKNOWN",
                    "bullets": [],
                    "mitigations": bucket.get("mitigations", [])
                })
                continue
        
        impact_cards.append({
            "id": bucket_id,
            "risk_level": bucket.get("risk_level", "UNKNOWN"),
            "bullets": bucket.get("bullets", []),
            "mitigations": bucket.get("mitigations", [])
        })
    
    # Build privacy_snapshot
    privacy_snapshot_obj = {
        "privacy_snapshot": privacy_compliance.get("privacy_snapshot", ""),
        "data_categories": privacy_compliance.get("data_categories", []),
        "governance_checks": privacy_compliance.get("governance_checks", []),
        "compliance_notes": privacy_compliance.get("compliance_notes", [])
    }
    
    # Build evidence
    sast_analysis = fixture["analysis_results"].get("javascript_analysis", {})
    permissions_analysis = fixture["analysis_results"].get("permissions_analysis", {})
    
    evidence = {
        "host_access_summary": host_access_summary,
        "capability_flags": capability_flags,
        "external_domains": external_domains,
        "network_evidence": network_evidence,
        "webstore_metadata": metadata,
        "sast_summary_or_findings": sast_analysis.get("sast_analysis") or sast_analysis.get("sast_findings", {}),
        "permissions_summary": permissions_analysis
    }
    
    # Build raw (for debugging)
    raw = {
        "executive_summary": executive_summary,
        "impact_analysis": impact_analysis,
        "privacy_compliance": privacy_compliance
    }
    
    return {
        "meta": meta,
        "scorecard": scorecard,
        "highlights": highlights,
        "impact_cards": impact_cards,
        "privacy_snapshot": privacy_snapshot_obj,
        "evidence": evidence,
        "raw": raw
    }


def run_pipeline(fixture: Dict[str, Any]) -> Dict[str, Any]:
    """Run the full pipeline and return all outputs."""
    manifest = fixture["manifest"]
    analysis_results = fixture["analysis_results"]
    metadata = fixture.get("metadata", {})
    extension_id = fixture["extension_id"]
    scan_id = fixture["scan_id"]
    
    # Step 1: Build SignalPack
    print(f"  Building SignalPack for {extension_id}...")
    signal_pack_builder = SignalPackBuilder()
    signal_pack = signal_pack_builder.build(
        scan_id=scan_id,
        analysis_results=analysis_results,
        metadata=metadata,
        manifest=manifest,
        extension_id=extension_id,
    )
    
    # Step 2: Compute scores
    print(f"  Computing scores...")
    user_count = metadata.get("user_count")
    scoring_engine = ScoringEngine(weights_version="v1")
    scoring_result = scoring_engine.calculate_scores(
        signal_pack=signal_pack,
        manifest=manifest,
        user_count=user_count,
        permissions_analysis=analysis_results.get("permissions_analysis"),
    )

    # Deterministic context (used by fallbacks + debug output)
    impact_analyzer = ImpactAnalyzer()
    host_access_summary = impact_analyzer._classify_host_access_scope(manifest)
    external_domains = impact_analyzer._extract_external_domains(analysis_results)
    javascript_analysis = analysis_results.get("javascript_analysis", {})
    network_evidence = ImpactAnalyzer._extract_network_evidence_from_sast(javascript_analysis)
    capability_flags = impact_analyzer._compute_capability_flags(
        manifest=manifest,
        analysis_results=analysis_results,
        host_access_summary=host_access_summary,
        external_domains=external_domains,
        network_evidence=network_evidence,
    )

    # Step 3: Generate executive summary (LLM) + deterministic fallback
    print(f"  Generating executive summary...")
    summary_generator = SummaryGenerator()
    executive_summary_raw = summary_generator.generate(
        analysis_results=analysis_results,
        manifest=manifest,
        metadata=metadata,
        scan_id=scan_id,
        extension_id=extension_id,
    )

    score = int(getattr(scoring_result, "overall_score", 0) or 0)
    score_label = _map_score_label_from_risk_level(getattr(scoring_result, "risk_level", None).value if getattr(scoring_result, "risk_level", None) else "")
    host_scope_label = host_access_summary.get("host_scope_label", "UNKNOWN")

    executive_summary = (
        executive_summary_raw
        if isinstance(executive_summary_raw, dict) and executive_summary_raw
        else _fallback_executive_summary(score=score, score_label=score_label, host_scope_label=host_scope_label)
    )

    # Step 4: Generate impact analysis (LLM) + deterministic fallback from capability_flags
    print(f"  Generating impact analysis...")
    impact_analysis_raw = impact_analyzer.generate(
        analysis_results=analysis_results,
        manifest=manifest,
        extension_id=extension_id,
    )
    impact_analysis = (
        impact_analysis_raw
        if isinstance(impact_analysis_raw, dict) and impact_analysis_raw
        else _fallback_impact_from_capability_flags(
            capability_flags=capability_flags,
            external_domains=external_domains,
            network_evidence=network_evidence,
        )
    )

    # Step 5: Generate privacy compliance (LLM) + safe fallback
    print(f"  Generating privacy compliance...")
    privacy_analyzer = PrivacyComplianceAnalyzer()
    privacy_compliance_raw = privacy_analyzer.generate(
        analysis_results=analysis_results,
        manifest=manifest,
        extension_dir=None,
        webstore_metadata=metadata,
    )
    privacy_compliance = (
        privacy_compliance_raw
        if isinstance(privacy_compliance_raw, dict) and privacy_compliance_raw
        else {
            "privacy_snapshot": "",
            "data_categories": [],
            "governance_checks": [],
            "compliance_notes": [],
        }
    )
    
    return {
        "executive_summary": executive_summary,
        "impact_analysis": impact_analysis,
        "privacy_compliance": privacy_compliance,
        "scoring_result": scoring_result,
        "signal_pack": signal_pack,
        "host_access_summary": host_access_summary,
        "capability_flags": capability_flags,
        "external_domains": external_domains,
        "network_evidence": network_evidence,
    }


def print_summary(fixture: Dict[str, Any], pipeline_outputs: Dict[str, Any], report_view_model: Dict[str, Any]):
    """Print console summary for a test case."""
    host_scope_label = report_view_model["meta"]["host_scope_label"]
    score = report_view_model["scorecard"]["score"]
    score_label = report_view_model["scorecard"]["score_label"]
    
    print(f"\n{'='*80}")
    print(f"Case: {fixture['extension_id']}")
    print(f"{'='*80}")
    print(f"Host Scope: {host_scope_label}")
    print(f"Score: {score} ({score_label})")
    print(f"\nImpact Risk Levels:")
    for card in report_view_model["impact_cards"]:
        print(f"  - {card['id']}: {card['risk_level']}")
    
    # Check for ALL_WEBSITES governance WARN
    if host_scope_label == "ALL_WEBSITES":
        governance_checks = report_view_model["privacy_snapshot"].get("governance_checks", [])
        broad_terms = ["broad", "all websites", "all_urls", "<all_urls>", "*://*/*"]
        has_broad_warn = False
        for chk in governance_checks:
            if not isinstance(chk, dict):
                continue
            status = str(chk.get("status", "")).upper()
            if status not in ("WARN", "FAIL"):
                continue
            hay = f"{chk.get('check','')} {chk.get('note','')}".lower()
            if any(t in hay for t in broad_terms):
                has_broad_warn = True
                break
        print(f"\nPrivacy Governance:")
        print(f"  - Has WARN for broad access: {has_broad_warn}")
        if not has_broad_warn:
            print(f"    ⚠️  WARNING: Expected governance_check mentioning broad access for ALL_WEBSITES")


def main():
    """Main entry point."""
    print("Generating UI report payloads...")
    print("="*80)
    
    # Create output directory
    output_dir = Path(__file__).parent.parent / "docs" / "ui_payload_examples"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Test Case A: ALL_WEBSITES
    print("\n[TEST CASE A] ALL_WEBSITES")
    fixture_a = create_test_fixture_all_websites()
    pipeline_outputs_a = run_pipeline(fixture_a)
    
    report_view_model_a = build_report_view_model(
        fixture=fixture_a,
        executive_summary=pipeline_outputs_a["executive_summary"],
        impact_analysis=pipeline_outputs_a["impact_analysis"],
        privacy_compliance=pipeline_outputs_a["privacy_compliance"],
        scoring_result=pipeline_outputs_a["scoring_result"],
        signal_pack=pipeline_outputs_a["signal_pack"],
        host_access_summary=pipeline_outputs_a["host_access_summary"],
        capability_flags=pipeline_outputs_a["capability_flags"],
        external_domains=pipeline_outputs_a["external_domains"],
        network_evidence=pipeline_outputs_a["network_evidence"],
    )
    
    output_a = {
        "report_view_model": report_view_model_a,
        "debug_inputs": {
            "host_access_summary_json": json.dumps(pipeline_outputs_a["host_access_summary"], indent=2, sort_keys=True),
            "capability_flags_json": json.dumps(pipeline_outputs_a["capability_flags"], indent=2, sort_keys=True),
            "external_domains_json": json.dumps(pipeline_outputs_a["external_domains"], indent=2, sort_keys=True),
            "network_evidence_json": json.dumps(pipeline_outputs_a["network_evidence"], indent=2, sort_keys=True),
        }
    }
    
    output_file_a = output_dir / "report_all_websites.json"
    with open(output_file_a, "w", encoding="utf-8") as f:
        json.dump(output_a, f, indent=2, ensure_ascii=True)
    
    print_summary(fixture_a, pipeline_outputs_a, report_view_model_a)
    print(f"\n✅ Written: {output_file_a}")
    
    # Test Case B: SINGLE_DOMAIN
    print("\n\n[TEST CASE B] SINGLE_DOMAIN")
    fixture_b = create_test_fixture_single_domain()
    pipeline_outputs_b = run_pipeline(fixture_b)
    
    report_view_model_b = build_report_view_model(
        fixture=fixture_b,
        executive_summary=pipeline_outputs_b["executive_summary"],
        impact_analysis=pipeline_outputs_b["impact_analysis"],
        privacy_compliance=pipeline_outputs_b["privacy_compliance"],
        scoring_result=pipeline_outputs_b["scoring_result"],
        signal_pack=pipeline_outputs_b["signal_pack"],
        host_access_summary=pipeline_outputs_b["host_access_summary"],
        capability_flags=pipeline_outputs_b["capability_flags"],
        external_domains=pipeline_outputs_b["external_domains"],
        network_evidence=pipeline_outputs_b["network_evidence"],
    )
    
    output_b = {
        "report_view_model": report_view_model_b,
        "debug_inputs": {
            "host_access_summary_json": json.dumps(pipeline_outputs_b["host_access_summary"], indent=2, sort_keys=True),
            "capability_flags_json": json.dumps(pipeline_outputs_b["capability_flags"], indent=2, sort_keys=True),
            "external_domains_json": json.dumps(pipeline_outputs_b["external_domains"], indent=2, sort_keys=True),
            "network_evidence_json": json.dumps(pipeline_outputs_b["network_evidence"], indent=2, sort_keys=True),
        }
    }
    
    output_file_b = output_dir / "report_single_domain.json"
    with open(output_file_b, "w", encoding="utf-8") as f:
        json.dump(output_b, f, indent=2, ensure_ascii=True)
    
    print_summary(fixture_b, pipeline_outputs_b, report_view_model_b)
    print(f"\n✅ Written: {output_file_b}")
    
    print(f"\n{'='*80}")
    print("✅ All report payloads generated successfully!")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()

