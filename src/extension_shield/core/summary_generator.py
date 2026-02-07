"""
Summary Generator

Generates executive summaries from all analysis results with overall risk assessment.
"""

import os
import json
import logging
from typing import Dict, Optional, Any
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from extension_shield.llm.prompts import get_prompts
from extension_shield.llm.clients.fallback import invoke_with_fallback

load_dotenv()
logger = logging.getLogger(__name__)


class SummaryGenerator:
    """Generates executive summaries from all analysis results."""

    @staticmethod
    def _map_risk_label(risk_level: str) -> str:
        """Map internal risk level to prompt label."""
        risk_level = (risk_level or "").lower()
        if risk_level in ("critical", "high"):
            return "HIGH RISK"
        if risk_level == "medium":
            return "MEDIUM RISK"
        return "LOW RISK"

    @staticmethod
    def _normalize_label_to_level(score_label: str) -> str:
        """Map prompt label to legacy risk level."""
        label = (score_label or "").upper()
        if label.startswith("HIGH"):
            return "high"
        if label.startswith("MEDIUM"):
            return "medium"
        return "low"

    @staticmethod
    def _json_block(value: Optional[Dict]) -> str:
        """Serialize a dict to a stable JSON block for prompt injection."""
        try:
            return json.dumps(value or {}, indent=2, sort_keys=True, ensure_ascii=True)
        except (TypeError, ValueError):
            return json.dumps(str(value), ensure_ascii=True)

    @staticmethod
    def _classify_host_access_scope(manifest: Dict) -> Dict[str, Any]:
        """
        Classify host access scope from manifest data.
        
        Returns:
            Dict with:
            - host_scope_label: "ALL_WEBSITES" | "MULTI_DOMAIN" | "SINGLE_DOMAIN" | "NONE"
            - patterns_count: Total number of host permission patterns
            - domains: Top 10 unique domains (if applicable)
            - has_all_urls: True if broad host access is present
        """
        # Broad patterns that indicate all websites access
        broad_patterns = [
            "<all_urls>",
            "*://*/*",
            "http://*/*",
            "https://*/*",
            "file:///*",
        ]
        
        # Get host permissions (MV3) or from permissions array (MV2)
        host_permissions = manifest.get("host_permissions", [])
        if not host_permissions:
            # Check permissions array for URL patterns (MV2)
            permissions = manifest.get("permissions", [])
            url_indicators = ["://", "*://", "http://", "https://", "file://", "ftp://", "<all_urls>"]
            host_permissions = [
                p for p in permissions
                if isinstance(p, str) and any(ind in p for ind in url_indicators)
            ]
        
        if not host_permissions:
            return {
                "host_scope_label": "NONE",
                "patterns_count": 0,
                "domains": [],
                "has_all_urls": False,
            }
        
        # Check for broad patterns
        has_all_urls = "<all_urls>" in host_permissions
        has_broad = any(pattern in host_permissions for pattern in broad_patterns)
        if has_broad:
            return {
                "host_scope_label": "ALL_WEBSITES",
                "patterns_count": len(host_permissions),
                "domains": [],
                "has_all_urls": has_all_urls,
            }
        
        # Extract unique domains from specific patterns
        import re
        domains = set()
        for pattern in host_permissions:
            # Extract domain from patterns like "https://*.example.com/*" or "https://example.com/*"
            match = re.search(r"(?:https?://)?(?:\*\.)?([a-zA-Z0-9][-a-zA-Z0-9]*(?:\.[a-zA-Z0-9][-a-zA-Z0-9]*)+)", pattern)
            if match:
                domains.add(match.group(1).lower())
        
        domain_count = len(domains)
        top_domains = sorted(domains)[:10]
        
        if domain_count == 0:
            # Couldn't extract domains, but has patterns - treat as multi-domain
            return {
                "host_scope_label": "MULTI_DOMAIN",
                "patterns_count": len(host_permissions),
                "domains": [],
                "has_all_urls": has_all_urls,
            }
        if domain_count == 1:
            return {
                "host_scope_label": "SINGLE_DOMAIN",
                "patterns_count": len(host_permissions),
                "domains": top_domains,
                "has_all_urls": has_all_urls,
            }
        return {
            "host_scope_label": "MULTI_DOMAIN",
            "patterns_count": len(host_permissions),
            "domains": top_domains,
            "has_all_urls": has_all_urls,
        }

    def _compute_score_context(
        self,
        analysis_results: Dict,
        manifest: Dict,
        metadata: Optional[Dict],
        scan_id: Optional[str],
        extension_id: Optional[str],
    ) -> tuple[int, str]:
        """Compute score + label for summary prompt, with safe fallback."""
        score = 0
        score_label = "LOW RISK"

        try:
            from extension_shield.governance.tool_adapters import SignalPackBuilder
            from extension_shield.scoring.engine import ScoringEngine

            signal_pack_builder = SignalPackBuilder()
            signal_pack = signal_pack_builder.build(
                scan_id=scan_id or "summary",
                analysis_results=analysis_results,
                metadata=metadata or {},
                manifest=manifest or {},
                extension_id=extension_id,
            )

            user_count = signal_pack.webstore_stats.installs
            if user_count is None and metadata:
                raw_count = metadata.get("user_count") or metadata.get("users")
                if raw_count is not None:
                    try:
                        user_count = int(str(raw_count).replace(",", "").replace("+", ""))
                    except ValueError:
                        user_count = None

            scoring_engine = ScoringEngine(weights_version="v1")
            scoring_result = scoring_engine.calculate_scores(
                signal_pack=signal_pack,
                manifest=manifest,
                user_count=user_count,
                permissions_analysis=analysis_results.get("permissions_analysis"),
            )

            score = int(scoring_result.overall_score)
            score_label = self._map_risk_label(scoring_result.risk_level.value)
        except Exception as exc:
            logger.warning("Failed to compute score context for summary: %s", exc)
            score = 0
            score_label = "HIGH RISK"

        return score, score_label

    def _get_summary_prompt_template(
        self,
        analysis_results: Dict,
        manifest: Dict,
        metadata: Optional[Dict],
        scan_id: Optional[str],
        extension_id: Optional[str],
    ) -> PromptTemplate:
        """Create prompt template for summary generation."""
        template_str = get_prompts("summary_generation")
        template_str = template_str.get("summary_generation")

        if not template_str:
            raise ValueError("Summary generation prompt template not found")

        score, score_label = self._compute_score_context(
            analysis_results=analysis_results,
            manifest=manifest,
            metadata=metadata,
            scan_id=scan_id,
            extension_id=extension_id,
        )

        manifest_json = self._json_block(manifest)
        permissions_summary_json = self._json_block(analysis_results.get("permissions_analysis"))
        webstore_result_json = self._json_block(analysis_results.get("webstore_analysis"))
        sast_result_json = self._json_block(analysis_results.get("javascript_analysis"))
        
        # Classify host access scope
        host_access_summary = self._classify_host_access_scope(manifest)
        host_access_summary_json = self._json_block(host_access_summary)

        template = PromptTemplate(
            input_variables=[
                "score",
                "score_label",
                "host_access_summary_json",
                "manifest_json",
                "permissions_summary_json",
                "webstore_result_json",
                "sast_result_json",
            ],
            template=template_str,
            template_format="jinja2",
        ).partial(
            score=score,
            score_label=score_label,
            host_access_summary_json=host_access_summary_json,
            manifest_json=manifest_json,
            permissions_summary_json=permissions_summary_json,
            webstore_result_json=webstore_result_json,
            sast_result_json=sast_result_json,
        )

        return template

    def generate(
        self,
        analysis_results: Dict,
        manifest: Dict,
        metadata: Optional[Dict] = None,
        scan_id: Optional[str] = None,
        extension_id: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        Generate executive summary from all analysis results.

        Args:
            analysis_results: Dict containing results from all analyzers
            manifest: Parsed manifest.json data
            metadata: Extension metadata (optional)
            scan_id: Scan identifier for scoring context (optional)
            extension_id: Extension ID for scoring context (optional)

        Returns:
            Dict with executive summary including:
                - overall_risk_level: "low" | "medium" | "high"
                - summary: Executive summary text
                - key_findings: List of critical findings
                - recommendations: List of actionable recommendations
        """
        if not analysis_results:
            logger.warning("No analysis results provided for summary generation")
            return None

        if not manifest:
            logger.warning("No manifest data provided for summary generation")
            return None

        prompt = self._get_summary_prompt_template(
            analysis_results=analysis_results,
            manifest=manifest,
            metadata=metadata,
            scan_id=scan_id,
            extension_id=extension_id,
        )
        model_name = os.getenv("LLM_MODEL", "rits/openai/gpt-oss-120b")
        model_parameters = {
            "temperature": 0.05,
            "max_tokens": 4096,
        }

        try:
            # Format prompt to messages
            formatted_prompt = prompt.format_prompt({})
            messages = formatted_prompt.to_messages()

            # Invoke with fallback
            response = invoke_with_fallback(
                messages=messages,
                model_name=model_name,
                model_parameters=model_parameters,
            )

            # Parse JSON response
            parser = JsonOutputParser()
            summary = parser.parse(response.content if hasattr(response, "content") else str(response))
            if isinstance(summary, dict):
                score = summary.get("score")
                score_label = summary.get("score_label")
                if score is None:
                    score, score_label = self._compute_score_context(
                        analysis_results=analysis_results,
                        manifest=manifest,
                        metadata=metadata,
                        scan_id=scan_id,
                        extension_id=extension_id,
                    )
                    summary["score"] = score
                    summary["score_label"] = score_label

                summary.setdefault("summary", summary.get("one_liner"))
                summary.setdefault("key_findings", summary.get("why_this_score", []))
                summary.setdefault("recommendations", summary.get("what_to_watch", []))
                summary.setdefault(
                    "overall_risk_level",
                    self._normalize_label_to_level(summary.get("score_label", "")),
                )
                summary.setdefault("overall_security_score", summary.get("score", 0))
            logger.info("Executive summary generated successfully")
            return summary
        except Exception as exc:
            logger.exception("Failed to generate executive summary: %s", exc)
            return None
