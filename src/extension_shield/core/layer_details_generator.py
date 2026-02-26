"""
Layer Details Generator

Generates human-friendly explanations for each layer (Security, Privacy, Governance)
based on analysis results. Uses LLM with structured output and deterministic fallback.
"""

import os
import json
import logging
from typing import Dict, Optional, Any, List
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from extension_shield.llm.prompts import get_prompts
from extension_shield.llm.clients.fallback import invoke_with_fallback
from extension_shield.llm.validators import ValidationResult
from extension_shield.scoring.models import ScoringResult, LayerScore
from extension_shield.scoring.gates import GateResult

load_dotenv()
logger = logging.getLogger(__name__)


class LayerDetailsGenerator:
    """Generates human-friendly layer details from scoring results."""

    @staticmethod
    def _json_block(value: Optional[Dict]) -> str:
        """Serialize a dict to a stable JSON block for prompt injection."""
        try:
            return json.dumps(value or {}, indent=2, sort_keys=True, ensure_ascii=True)
        except (TypeError, ValueError):
            return json.dumps(str(value), ensure_ascii=True)

    @staticmethod
    def _extract_layer_gates(gate_results: List[GateResult], layer: str) -> List[Dict[str, Any]]:
        """Extract gate results for a specific layer."""
        # Gate to layer mapping based on existing patterns
        gate_layer_map = {
            "CRITICAL_SAST": "security",
            "VT_MALWARE": "security", 
            "MANIFEST_POSTURE": "security",
            "SENSITIVE_EXFIL": "privacy",
            "CAPTURE_SIGNALS": "privacy",
            "PURPOSE_MISMATCH": "governance",
            "TOS_VIOLATION": "governance",
        }
        
        layer_gates = []
        for gate in gate_results:
            if gate_layer_map.get(gate.gate_id) == layer and gate.triggered:
                layer_gates.append({
                    "gate_id": gate.gate_id,
                    "decision": gate.decision,
                    "confidence": gate.confidence,
                    "reasons": gate.reasons,
                    "details": gate.details
                })
        
        return layer_gates

    @staticmethod
    def _get_risk_level_from_score(score: int) -> str:
        """Map score to risk level. Red: 0-49, Yellow: 50-74, Green: 75-100."""
        if score >= 75:
            return "LOW"
        elif score >= 50:
            return "MEDIUM"
        else:
            return "HIGH"

    def _get_layer_details_prompt_template(
        self,
        scoring_result: ScoringResult,
        analysis_results: Dict,
        manifest: Dict,
        gate_results: List[GateResult],
    ) -> PromptTemplate:
        """Build the layer details prompt template with all required data."""
        
        # Get layer scores and risk levels
        security_score = scoring_result.security_score
        privacy_score = scoring_result.privacy_score
        governance_score = scoring_result.governance_score
        
        security_risk = self._get_risk_level_from_score(security_score)
        privacy_risk = self._get_risk_level_from_score(privacy_score)
        governance_risk = self._get_risk_level_from_score(governance_score)
        
        # Extract factors for each layer
        security_factors = []
        privacy_factors = []
        governance_factors = []
        
        if scoring_result.security_layer:
            security_factors = [factor.model_dump() for factor in scoring_result.security_layer.factors]
        if scoring_result.privacy_layer:
            privacy_factors = [factor.model_dump() for factor in scoring_result.privacy_layer.factors]
        if scoring_result.governance_layer:
            governance_factors = [factor.model_dump() for factor in scoring_result.governance_layer.factors]
        
        # Extract gates for each layer
        security_gates = self._extract_layer_gates(gate_results, "security")
        privacy_gates = self._extract_layer_gates(gate_results, "privacy")
        governance_gates = self._extract_layer_gates(gate_results, "governance")
        
        # Get analysis context
        permissions_summary = analysis_results.get("permissions_analysis", {})
        host_access_summary = self._classify_host_access_scope(manifest)
        sast_result = analysis_results.get("javascript_analysis", {})
        network_evidence = self._extract_network_evidence(analysis_results)
        
        # Load the prompt template
        prompts = get_prompts("layer_details_generation")
        prompt_text = prompts.get("layer_details_generation", "")
        
        if not prompt_text:
            raise ValueError("layer_details_generation prompt not found")
        
        # Use jinja2 format since YAML templates use {{ variable }} syntax
        template = PromptTemplate(
            input_variables=[
                "security_score", "security_risk_level", "security_factors_json", "security_gates_json",
                "privacy_score", "privacy_risk_level", "privacy_factors_json", "privacy_gates_json",
                "governance_score", "governance_risk_level", "governance_factors_json", "governance_gates_json",
                "permissions_summary_json", "host_access_summary_json", "sast_result_json",
                "network_evidence_json", "manifest_json",
            ],
            template=prompt_text,
            template_format="jinja2",
        )
        
        # Fill in template variables
        template = template.partial(
            security_score=security_score,
            security_risk_level=security_risk,
            security_factors_json=self._json_block(security_factors),
            security_gates_json=self._json_block(security_gates),
            
            privacy_score=privacy_score,
            privacy_risk_level=privacy_risk,
            privacy_factors_json=self._json_block(privacy_factors),
            privacy_gates_json=self._json_block(privacy_gates),
            
            governance_score=governance_score,
            governance_risk_level=governance_risk,
            governance_factors_json=self._json_block(governance_factors),
            governance_gates_json=self._json_block(governance_gates),
            
            permissions_summary_json=self._json_block(permissions_summary),
            host_access_summary_json=self._json_block(host_access_summary),
            sast_result_json=self._json_block(sast_result),
            network_evidence_json=self._json_block(network_evidence),
            manifest_json=self._json_block(manifest),
        )

        return template

    @staticmethod
    def _classify_host_access_scope(manifest: Dict) -> Dict[str, Any]:
        """Classify host access scope from manifest data."""
        # Reuse the same logic as SummaryGenerator for consistency
        broad_patterns = [
            "<all_urls>",
            "*://*/*", 
            "http://*/*",
            "https://*/*",
            "file:///*",
        ]
        
        host_permissions = manifest.get("host_permissions", [])
        if not host_permissions:
            permissions = manifest.get("permissions", [])
            url_indicators = ["://", "*://", "http://", "https://", "file://", "ftp://", "<all_urls>"]
            host_permissions = [
                p for p in permissions
                if isinstance(p, str) and any(ind in p for ind in url_indicators)
            ]
        
        has_all_urls = any(
            any(pattern in str(perm) for pattern in broad_patterns)
            for perm in host_permissions
        )
        
        if has_all_urls:
            return {
                "host_scope_label": "ALL_WEBSITES",
                "patterns_count": len(host_permissions),
                "has_all_urls": True
            }
        elif len(host_permissions) > 1:
            return {
                "host_scope_label": "MULTI_DOMAIN", 
                "patterns_count": len(host_permissions),
                "has_all_urls": False
            }
        elif len(host_permissions) == 1:
            return {
                "host_scope_label": "SINGLE_DOMAIN",
                "patterns_count": 1,
                "has_all_urls": False
            }
        else:
            return {
                "host_scope_label": "NONE",
                "patterns_count": 0,
                "has_all_urls": False
            }

    @staticmethod
    def _extract_network_evidence(analysis_results: Dict) -> List[Dict[str, Any]]:
        """Extract network evidence from analysis results."""
        network_evidence = []
        
        # Extract from SAST results
        sast_results = analysis_results.get("javascript_analysis", {})
        if isinstance(sast_results, dict):
            findings = sast_results.get("findings", [])
            for finding in findings:
                if isinstance(finding, dict) and "network" in str(finding).lower():
                    network_evidence.append({
                        "type": "sast_finding",
                        "description": finding.get("description", ""),
                        "category": finding.get("category", ""),
                        "severity": finding.get("severity", "")
                    })
        
        # Extract from network analyzer if present
        network_results = analysis_results.get("network_analysis", {})
        if isinstance(network_results, dict):
            requests = network_results.get("requests", [])
            for request in requests:
                if isinstance(request, dict):
                    network_evidence.append({
                        "type": "network_request", 
                        "url": request.get("url", ""),
                        "method": request.get("method", ""),
                    })
        
        return network_evidence

    def generate(
        self,
        scoring_result: ScoringResult,
        analysis_results: Dict,
        manifest: Dict,
        gate_results: Optional[List[GateResult]] = None,
    ) -> Optional[Dict]:
        """
        Generate layer details from scoring results.

        Args:
            scoring_result: Complete scoring result with layer breakdowns
            analysis_results: Dict containing results from all analyzers  
            manifest: Parsed manifest.json data
            gate_results: List of gate evaluation results

        Returns:
            Dict with layer details:
            {
                "security": {"one_liner": str, "key_points": [str], "what_to_watch": [str]},
                "privacy": {"one_liner": str, "key_points": [str], "what_to_watch": [str]},
                "governance": {"one_liner": str, "key_points": [str], "what_to_watch": [str]}
            }
        """
        if not scoring_result:
            logger.warning("No scoring result provided for layer details generation")
            return None

        if not analysis_results:
            logger.warning("No analysis results provided for layer details generation")
            return None

        if not manifest:
            logger.warning("No manifest data provided for layer details generation")
            return None

        try:
            prompt = self._get_layer_details_prompt_template(
                scoring_result=scoring_result,
                analysis_results=analysis_results,
                manifest=manifest,
                gate_results=gate_results or [],
            )
            
            # Use OpenAI 4-1 (gpt-4o) for better human-readable output
            model_name = os.getenv("LLM_MODEL", "gpt-4o")
            model_parameters = {
                "temperature": 0.3,  # Higher temperature for more natural, conversational language
                "max_tokens": 4096,
            }

            # Format prompt to messages
            formatted_prompt = prompt.format_prompt()
            messages = formatted_prompt.to_messages()

            # Invoke with fallback
            response = invoke_with_fallback(
                messages=messages,
                model_name=model_name,
                model_parameters=model_parameters,
            )

            # Parse JSON response
            parser = JsonOutputParser()
            layer_details = parser.parse(response.content if hasattr(response, "content") else str(response))
            
            if isinstance(layer_details, dict):
                # Validate the output
                validation = self._validate_layer_details(
                    layer_details, scoring_result, analysis_results, manifest, gate_results or []
                )
                
                if validation.ok:
                    logger.info("Layer details generation successful")
                    return layer_details
                else:
                    logger.warning(
                        "LLM layer details validation failed, using fallback. Reasons: %s",
                        validation.reasons
                    )
                    return None
            else:
                logger.warning("LLM returned non-dict response for layer details")
                return None

        except Exception as exc:
            logger.warning("Layer details generation failed: %s", exc)
            return None

    def _validate_layer_details(
        self,
        output: Dict[str, Any],
        scoring_result: ScoringResult,
        analysis_results: Dict,
        manifest: Dict,
        gate_results: List[GateResult],
    ) -> ValidationResult:
        """Validate layer details output."""
        reasons = []

        # Check structure
        required_layers = ["security", "privacy", "governance"]
        for layer in required_layers:
            if layer not in output:
                reasons.append(f"Missing {layer} layer in output")
                continue
            
            layer_data = output[layer]
            if not isinstance(layer_data, dict):
                reasons.append(f"{layer} layer is not a dict")
                continue
            
            required_fields = ["one_liner", "key_points", "what_to_watch"]
            for field in required_fields:
                if field not in layer_data:
                    reasons.append(f"Missing {field} in {layer} layer")

        # Check lengths
        for layer_name in required_layers:
            if layer_name not in output:
                continue
            layer_data = output[layer_name]
            
            one_liner = layer_data.get("one_liner", "")
            if len(one_liner) > 150:
                reasons.append(f"{layer_name}.one_liner exceeds 150 characters")
            
            for bullet_list_name in ["key_points", "what_to_watch"]:
                bullets = layer_data.get(bullet_list_name, [])
                if not isinstance(bullets, list):
                    continue
                    
                for i, bullet in enumerate(bullets):
                    if isinstance(bullet, str) and len(bullet) > 120:
                        reasons.append(f"{layer_name}.{bullet_list_name}[{i}] exceeds 120 characters")

        # Check for generic filler
        banned_phrases = [
            "score is based on",
            "this analysis", 
            "capabilities indicate",
            "review the notes",
            "code signals",
            "store metadata"
        ]
        
        all_text = json.dumps(output).lower()
        for phrase in banned_phrases:
            if phrase in all_text:
                reasons.append(f"Contains generic filler phrase: '{phrase}'")

        # Check for concrete references
        # This validation ensures bullets reference actual signals
        concrete_signals = self._extract_concrete_signals(
            scoring_result, analysis_results, manifest, gate_results
        )
        
        for layer_name in required_layers:
            if layer_name not in output:
                continue
            layer_data = output[layer_name]
            
            for bullet_list_name in ["key_points", "what_to_watch"]:
                bullets = layer_data.get(bullet_list_name, [])
                if not isinstance(bullets, list):
                    continue
                    
                for i, bullet in enumerate(bullets):
                    if isinstance(bullet, str) and bullet.strip():
                        bullet_lower = bullet.lower()
                        # Check if bullet contains at least one concrete signal
                        has_concrete_reference = any(
                            signal.lower() in bullet_lower for signal in concrete_signals
                        )
                        if not has_concrete_reference:
                            reasons.append(f"{layer_name}.{bullet_list_name}[{i}] lacks concrete signal reference")
                            continue

                        # If bullet mentions a gate, require a human explanation
                        gate_ids = [
                            "CRITICAL_SAST",
                            "VT_MALWARE",
                            "SENSITIVE_EXFIL",
                            "PURPOSE_MISMATCH",
                            "TOS_VIOLATION",
                            "MANIFEST_POSTURE",
                            "CAPTURE_SIGNALS",
                        ]
                        for gate_id in gate_ids:
                            if gate_id.lower() in bullet_lower:
                                parts = bullet_lower.split(gate_id.lower(), 1)
                                text_after_gate = parts[1].strip() if len(parts) > 1 else ""
                                if len(text_after_gate) < 20 or text_after_gate in ["detected", "triggered", "found", "present"]:
                                    reasons.append(
                                        f"{layer_name}.{bullet_list_name}[{i}] mentions {gate_id} but lacks human explanation"
                                    )

                        # If bullet mentions a permission/host, require a human explanation
                        common_permissions = [
                            "cookies",
                            "webrequest",
                            "activetab",
                            "tabs",
                            "storage",
                            "history",
                            "bookmarks",
                            "all_urls",
                            "<all_urls>",
                            "https://*/*",
                            "*://*/*",
                        ]
                        permission_patterns = [
                            "permission",
                            "perm",
                            "can ",
                            "can access",
                            "can read",
                            "can write",
                            "can modify",
                            "requests ",
                            "has ",
                            "uses ",
                        ]
                        for perm in common_permissions:
                            if perm in bullet_lower:
                                has_explanation = any(pattern in bullet_lower for pattern in permission_patterns) or (
                                    len(bullet_lower.replace(perm, "").strip()) > 15
                                )
                                if not has_explanation:
                                    words = bullet_lower.split()
                                    if perm in words and len(words) <= 3:
                                        reasons.append(
                                            f"{layer_name}.{bullet_list_name}[{i}] mentions {perm} but lacks human explanation"
                                        )

        return ValidationResult(ok=len(reasons) == 0, reasons=reasons)

    def _extract_concrete_signals(
        self,
        scoring_result: ScoringResult,
        analysis_results: Dict,
        manifest: Dict,
        gate_results: List[GateResult],
    ) -> List[str]:
        """Extract concrete signal names that should be referenced in explanations."""
        signals = []
        
        # Add gate IDs
        for gate in gate_results:
            if gate.triggered:
                signals.append(gate.gate_id)
        
        # Add permissions
        permissions = manifest.get("permissions", []) + manifest.get("host_permissions", [])
        for perm in permissions:
            if isinstance(perm, str):
                signals.append(perm)
        
        # Add common permission names
        common_permissions = [
            "cookies", "webRequest", "activeTab", "tabs", "storage", "history", 
            "bookmarks", "webNavigation", "webRequestBlocking", "proxy",
            "<all_urls>", "https://*/*", "*://*/*"
        ]
        signals.extend(common_permissions)
        
        # Add factor names from scoring result
        for layer in [scoring_result.security_layer, scoring_result.privacy_layer, scoring_result.governance_layer]:
            if layer:
                for factor in layer.factors:
                    signals.append(factor.name)
        
        return signals

