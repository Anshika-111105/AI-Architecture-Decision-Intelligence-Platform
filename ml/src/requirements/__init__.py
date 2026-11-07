"""
ADIP Requirement Intelligence Package (Phase 5)
Lead Deliverable — Anshika (AI/ML & Data Intelligence Lead)

Exports schemas, normalization utilities, prompt specifications,
and the dual-path extraction engine for converting unstructured or structured
inputs into validated architecture requirements.
"""

from ml.src.requirements.schemas import (
    DomainType,
    WorkloadType,
    RawExtractedRequirements,
    NormalizedRequirement,
    RequirementAnalysisResponse,
)
from ml.src.requirements.normalizer import RequirementNormalizer
from ml.src.requirements.prompts import (
    EXTRACTION_SYSTEM_PROMPT,
    FEW_SHOT_EXAMPLES,
    build_extraction_prompt,
    get_schema_description,
)
from ml.src.requirements.extractor import RequirementExtractor

__all__ = [
    "DomainType",
    "WorkloadType",
    "RawExtractedRequirements",
    "NormalizedRequirement",
    "RequirementAnalysisResponse",
    "RequirementNormalizer",
    "RequirementExtractor",
    "EXTRACTION_SYSTEM_PROMPT",
    "FEW_SHOT_EXAMPLES",
    "build_extraction_prompt",
    "get_schema_description",
]
