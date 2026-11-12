"""
ADIP Requirement Intelligence Extractor (Phase 5)
Lead Deliverable — Anshika (AI/ML & Data Intelligence Lead)

Implements Dual-Path Requirement Intelligence (Section 6.1):
  1. Form Path (Deterministic): Directly normalizes and validates structured form input.
  2. Free-Text NLP Path: Uses LLM (OpenAI) with structured system prompt and few-shot examples,
     automatic retry on malformed JSON (Section 7.2), and a deterministic offline heuristic fallback.
"""

import os
import re
import json
import logging
from typing import Dict, Any, Optional, Tuple, List

from ml.src.requirements.schemas import (
    NormalizedRequirement,
    RawExtractedRequirements,
    RequirementAnalysisResponse,
    DomainType,
    WorkloadType,
)
from ml.src.requirements.normalizer import RequirementNormalizer
from ml.src.requirements.prompts import (
    build_extraction_prompt,
    EXTRACTION_SYSTEM_PROMPT,
)

logger = logging.getLogger("ADIP_RequirementExtractor")


class RequirementExtractor:
    """
    Core engine for converting free-form text or structured forms into
    validated, standardized architecture requirements.
    """

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        max_retries: int = 1,
    ):
        self.api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.max_retries = max_retries
        self.normalizer = RequirementNormalizer()

    # -------------------------------------------------------------------------
    # Path A: Form Extraction (Section 6.1)
    # -------------------------------------------------------------------------
    def extract_from_form(
        self,
        form_data: Dict[str, Any],
        project_id: Optional[str] = None
    ) -> RequirementAnalysisResponse:
        """
        Bypasses LLM; directly normalizes and validates structured form submissions.
        Ensures unstated fields remain null and are tracked in missing_fields.
        """
        normalized, missing_fields, assumptions = self.normalizer.normalize_requirements(
            raw_input=form_data,
            project_id=project_id,
        )

        is_complete = self._assess_completeness(normalized)

        return RequirementAnalysisResponse(
            requirements=normalized,
            missing_fields=missing_fields,
            assumptions=assumptions,
            is_complete=is_complete,
            raw_input=json.dumps(form_data, default=str),
        )

    # -------------------------------------------------------------------------
    # Path B: Natural-Language Free-Text Extraction (Section 6.1 & 6.2)
    # -------------------------------------------------------------------------
    def extract_from_text(
        self,
        text: str,
        project_id: Optional[str] = None
    ) -> RequirementAnalysisResponse:
        """
        Extracts requirements from free-text using LLM prompt intelligence.
        Implements Section 7.2 retry logic on malformed output, with deterministic
        offline fallback if OpenAI is unconfigured or unreachable.
        """
        raw_dict: Optional[Dict[str, Any]] = None
        error_history: List[str] = []

        # Attempt OpenAI extraction if API key is present
        if self.api_key:
            raw_dict = self._call_openai_with_retry(text, error_history)

        # If LLM unavailable or failed, use deterministic offline regex extractor
        if raw_dict is None:
            logger.info("Using offline deterministic extractor for free-text input.")
            raw_dict = self._extract_offline_heuristics(text)

        # Normalize and validate extracted dict
        normalized, missing_fields, assumptions = self.normalizer.normalize_requirements(
            raw_input=raw_dict,
            project_id=project_id,
        )

        # If offline fallback was used, flag as assumption for full transparency
        if not self.api_key:
            assumptions.append("Extracted using offline deterministic heuristic parser (OPENAI_API_KEY not configured).")

        is_complete = self._assess_completeness(normalized)

        return RequirementAnalysisResponse(
            requirements=normalized,
            missing_fields=missing_fields,
            assumptions=assumptions,
            is_complete=is_complete,
            raw_input=text,
        )

    # -------------------------------------------------------------------------
    # LLM Calling & Retry Mechanism (Section 7.2)
    # -------------------------------------------------------------------------
    def _call_openai_with_retry(
        self,
        text: str,
        error_history: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Calls OpenAI API with structured prompt. Retries once if JSON is malformed
        or validation fails (Section 7.2).
        """
        try:
            import openai
        except ImportError:
            logger.warning("openai library not installed; falling back to offline extractor.")
            return None

        client = openai.OpenAI(api_key=self.api_key)
        messages = build_extraction_prompt(text)

        for attempt in range(self.max_retries + 1):
            try:
                response = client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0.0,
                )
                raw_content = response.choices[0].message.content
                if not raw_content:
                    raise ValueError("OpenAI returned empty response body.")

                # Clean markdown fences if any slipped past system prompt
                cleaned_content = re.sub(r"^```(?:json)?|```$", "", raw_content.strip()).strip()
                parsed_json = json.loads(cleaned_content)
                if isinstance(parsed_json, dict):
                    return parsed_json
                else:
                    raise ValueError("Parsed JSON is not a dictionary.")

            except Exception as e:
                err_msg = f"Attempt {attempt + 1} failed: {str(e)}"
                logger.warning(err_msg)
                error_history.append(err_msg)
                if attempt < self.max_retries:
                    # Append retry guidance message
                    messages.append({
                        "role": "user",
                        "content": (
                            "Your previous output could not be parsed as valid JSON. "
                            "Please output ONLY the raw JSON object conforming strictly to the requested schema."
                        )
                    })

        return None

    # -------------------------------------------------------------------------
    # Deterministic Offline Extraction Fallback
    # -------------------------------------------------------------------------
    def _extract_offline_heuristics(self, text: str) -> Dict[str, Any]:
        """
        Rule-based pattern extractor for deterministic, offline, and test execution.
        Safely neutralizes prompt-injection attempts and extracts core architecture parameters.
        """
        s = text.strip()
        lower_s = s.lower()
        extracted: Dict[str, Any] = {"raw_expressions": {}}

        # Prompt-injection check: if text is purely an attack string with no requirements, return empty
        injection_patterns = [
            r"ignore\s+(?:all\s+)?previous\s+instructions",
            r"print\s+(?:the\s+)?system\s+prompt",
            r"tell\s+me\s+secret",
            r"act\s+as\s+a\s+different\s+model",
        ]
        if any(re.search(pat, lower_s) for pat in injection_patterns):
            # If text has no architectural terms, return clean empty
            if not any(k in lower_s for k in ["rps", "user", "budget", "latency", "uptime", "data", "storage"]):
                return extracted

        # 1. Domain
        for phrase, canonical in RequirementNormalizer.DOMAIN_SYNONYMS.items():
            if re.search(r"\b" + re.escape(phrase) + r"\b", lower_s):
                extracted["domain"] = canonical
                break

        # 2. RPS (Requests per second)
        rps_match = re.search(
            r"(\d[\d,]*(?:\.\d+)?\s*(?:k|thousand|million|m)?)\s*(?:rps|req(?:uests)?\s*(?:per|/)\s*sec(?:ond)?)",
            lower_s
        )
        if rps_match:
            extracted["rps"] = rps_match.group(1).strip()
            extracted["raw_expressions"]["rps"] = rps_match.group(0).strip()

        # 3. Peak RPS (handles '5,000 peak RPS', 'peak of 5000 RPS', 'peak RPS: 5k')
        peak_match = re.search(
            r"(\d[\d,]*(?:\.\d+)?\s*(?:k|thousand|m)?)\s*peak\s*(?:rps|req(?:uests)?\s*(?:per|/)\s*sec(?:ond)?)?|(?:peak|spike)\s*(?:of|to|rps)?\s*[:=]?\s*(\d[\d,]*(?:\.\d+)?\s*(?:k|thousand|m)?)",
            lower_s
        )
        if peak_match:
            peak_val = (peak_match.group(1) or peak_match.group(2)).strip()
            extracted["peak_rps"] = peak_val
            extracted["raw_expressions"]["peak_rps"] = peak_match.group(0).strip()

        # 4. Users (registered, active, tenants, vehicles, etc.)
        users_match = re.search(
            r"(\d[\d,]*(?:\.\d+)?\s*(?:million|millions|m|billion|b|thousand|k|lakh|lakhs|crore|crores|cr)?)\s*(?:\w+\s+)?(?:users|tenants|accounts|clients|vehicles|trucks|devices|subscribers)",
            lower_s
        )
        if users_match:
            extracted["users"] = users_match.group(1).strip()
            extracted["raw_expressions"]["users"] = users_match.group(0).strip()

        # 5. Concurrency
        conc_match = re.search(
            r"(\d[\d,]*(?:\.\d+)?\s*(?:k|thousand)?)\s*(?:concurrent|simultaneous)\s*(?:users|sessions|connections)?",
            lower_s
        )
        if conc_match:
            extracted["concurrency"] = conc_match.group(1).strip()
            extracted["raw_expressions"]["concurrency"] = conc_match.group(0).strip()

        # 6. Data Size / Storage (TB, GB, MB, PB)
        storage_match = re.search(
            r"(\d[\d,]*(?:\.\d+)?\s*(?:tb|gb|mb|pb|terabytes?|gigabytes?|petabytes?))\s*(?:of\s+)?(?:data|storage|catalog|logs)?",
            lower_s
        )
        if storage_match:
            extracted["data_size"] = storage_match.group(1).strip()
            extracted["raw_expressions"]["data_size"] = storage_match.group(0).strip()

        # 7. Availability SLA / Uptime
        for text_nine in RequirementNormalizer.NINES_MAP:
            if text_nine in lower_s:
                extracted["availability_sla"] = text_nine
                extracted["raw_expressions"]["availability_sla"] = text_nine
                break
        if "availability_sla" not in extracted:
            avail_match = re.search(r"(\d{2}(?:\.\d+)?)\s*%\s*(?:uptime|availability)", lower_s)
            if avail_match:
                extracted["availability_sla"] = avail_match.group(1).strip()
                extracted["raw_expressions"]["availability_sla"] = avail_match.group(0).strip()

        # 8. Latency SLA
        lat_match = re.search(
            r"(?:latency\s*(?:under|<|below|sub|of)?\s*|sub-)(\d+)\s*(?:ms|millis|milliseconds)",
            lower_s
        )
        if lat_match:
            extracted["latency_sla"] = lat_match.group(1).strip()
            extracted["raw_expressions"]["latency_sla"] = lat_match.group(0).strip()

        # 9. Budget (Currency symbols, lakhs, USD)
        budget_match = re.search(
            r"(?:[₹$€£]\s*[\d,]+(?:\.\d+)?(?:\s*(?:lakh|lac|crore|cr|k|million|thousand))?|[\d,]+(?:\.\d+)?\s*(?:lakh|lac|crore|cr|k|million|thousand)?\s*(?:per\s+month|/month|monthly\s+budget|usd|inr))",
            lower_s
        )
        if budget_match:
            extracted["budget"] = budget_match.group(0).strip()
            extracted["raw_expressions"]["budget"] = budget_match.group(0).strip()

        # 10. Read / Write Ratio
        rw_match = re.search(r"(\d+[/:]\d+(?:\s*read/write)?|\d+%\s*(?:reads?|writes?))", lower_s)
        if rw_match:
            extracted["read_write_ratio"] = rw_match.group(1).strip()
            extracted["raw_expressions"]["read_write_ratio"] = rw_match.group(0).strip()

        # 11. Team Size
        team_match = re.search(r"team\s+(?:of\s+)?(\d+)\s*(?:engineers|devs|developers|people)?", lower_s)
        if team_match:
            extracted["team_size"] = team_match.group(1).strip()

        # 12. Workload Type
        for phrase, canonical in RequirementNormalizer.WORKLOAD_SYNONYMS.items():
            if re.search(r"\b" + re.escape(phrase) + r"\b", lower_s):
                extracted["workload_type"] = canonical
                break

        return extracted

    # -------------------------------------------------------------------------
    # Completeness Assessment
    # -------------------------------------------------------------------------
    @staticmethod
    def _assess_completeness(req: NormalizedRequirement) -> bool:
        """
        Assesses whether minimum viable inputs exist for architecture selection:
          - domain is known
          - traffic/scale is known (either users or rps or peak_rps)
          - operational SLA or budget is specified (availability_sla or budget or latency_sla)
        """
        has_domain = req.domain is not None
        has_scale = (req.users is not None) or (req.rps is not None) or (req.peak_rps is not None)
        has_constraint = (req.availability_sla is not None) or (req.budget is not None) or (req.latency_sla is not None)
        return bool(has_domain and has_scale and has_constraint)
