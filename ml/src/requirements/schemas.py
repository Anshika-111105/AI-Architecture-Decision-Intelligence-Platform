from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, model_validator


class DomainType(str, Enum):
    """Controlled vocabulary for software application domains."""
    ECOMMERCE = "ecommerce"
    FINTECH = "fintech"
    SOCIAL_NETWORK = "social_network"
    STREAMING = "streaming"
    IOT = "iot"
    HEALTHCARE = "healthcare"
    SAAS = "saas"
    OTHER = "other"


class WorkloadType(str, Enum):
    """Controlled vocabulary for operational traffic characteristics."""
    TRANSACTIONAL = "transactional"
    READ_HEAVY = "read_heavy"
    WRITE_HEAVY = "write_heavy"
    BALANCED = "balanced"
    STREAMING = "streaming"
    ANALYTICAL = "analytical"


class RawExtractedRequirements(BaseModel):
    """
    Intermediate representation parsed directly from user natural language or form.
    Fields the user did not mention remain None (null) and are never guessed.
    """
    domain: Optional[str] = Field(default=None, description="Application domain or industry category")
    users: Optional[int] = Field(default=None, description="Registered or total user count")
    concurrency: Optional[int] = Field(default=None, description="Concurrent users or active sessions")
    rps: Optional[float] = Field(default=None, description="Baseline request rate in requests per second")
    peak_rps: Optional[float] = Field(default=None, description="Peak request rate in requests per second")
    data_size: Optional[float] = Field(default=None, description="Initial or total data volume in Gigabytes (GB)")
    read_write_ratio: Optional[float] = Field(default=None, description="Read traffic fraction between 0.0 and 1.0")
    latency_sla: Optional[float] = Field(default=None, description="Target response latency limit in milliseconds")
    availability_sla: Optional[float] = Field(default=None, description="Target availability uptime percentage (e.g. 99.99)")
    budget: Optional[float] = Field(default=None, description="Monthly infrastructure budget")
    traffic_growth: Optional[float] = Field(default=None, description="Projected annual traffic growth percentage")
    team_size: Optional[int] = Field(default=None, description="Engineering/development team size")
    workload_type: Optional[str] = Field(default=None, description="Workload profile (transactional, read_heavy, etc.)")
    
    # Raw strings for non-standard expressions before normalization (e.g., '₹4 lakh', '50 TB')
    raw_expressions: Dict[str, str] = Field(default_factory=dict, description="Raw expressions captured from free text")


class NormalizedRequirement(BaseModel):
    """
    Canonical, validated requirements schema aligned with Dataset A (Requirements)
    and Dataset C (Workload). All units are standardized:
      - Users/Concurrency: Integer counts
      - RPS/Peak RPS: Requests per second (float >= 0.1)
      - Data Size: Gigabytes (GB)
      - Read/Write Ratio: [0.0, 1.0]
      - Latency SLA: Milliseconds (ms)
      - Availability SLA: Percentage [90.0, 100.0]
      - Budget: Monthly USD (float >= 0.0)
    """
    project_id: Optional[str] = Field(default=None, description="Unique project identifier")
    domain: Optional[str] = Field(default=None, description="Standardized domain category")
    users: Optional[int] = Field(default=None, ge=1, description="Registered user base (must be >= 1)")
    concurrency: Optional[int] = Field(default=None, ge=1, description="Concurrent active sessions (must be >= 1)")
    rps: Optional[float] = Field(default=None, ge=0.1, description="Requests per second (must be >= 0.1)")
    peak_rps: Optional[float] = Field(default=None, ge=0.1, description="Peak requests per second (must be >= 0.1)")
    data_size: Optional[float] = Field(default=None, ge=0.01, description="Data volume in Gigabytes GB (must be >= 0.01)")
    read_write_ratio: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Read ratio [0.0, 1.0]")
    latency_sla: Optional[float] = Field(default=None, ge=1.0, description="Latency SLA in ms (must be >= 1.0)")
    availability_sla: Optional[float] = Field(default=None, ge=90.0, le=100.0, description="Availability % [90.0, 100.0]")
    budget: Optional[float] = Field(default=None, ge=0.0, description="Monthly infrastructure budget in USD (must be >= 0.0)")
    traffic_growth: Optional[float] = Field(default=None, ge=0.0, description="Annual traffic growth % (must be >= 0.0)")
    team_size: Optional[int] = Field(default=None, ge=1, description="Team size (must be >= 1)")
    workload_type: Optional[str] = Field(default=None, description="Workload profile classification")

    @model_validator(mode="after")
    def validate_cross_field_rules(self) -> "NormalizedRequirement":
        """
        Enforces Section 7.1 Cross-Field Integrity Rules:
          1. peak_rps cannot be lower than baseline rps
          2. concurrency cannot exceed total users (if both are provided)
        """
        # Rule 1: peak_rps >= rps
        if self.rps is not None and self.peak_rps is not None:
            if self.peak_rps < self.rps:
                raise ValueError(
                    f"Cross-field validation failed: peak_rps ({self.peak_rps}) cannot be less than baseline rps ({self.rps})."
                )

        # Rule 2: concurrency <= users
        if self.concurrency is not None and self.users is not None:
            if self.concurrency > self.users:
                raise ValueError(
                    f"Cross-field validation failed: concurrency ({self.concurrency}) cannot exceed total users ({self.users})."
                )

        return self


class RequirementAnalysisResponse(BaseModel):
    """
    Standard output contract returned by Requirement Intelligence to FastAPI & React.
    Includes normalized requirements, unmentioned fields (never guessed),
    and flagged assumptions for user review.
    """
    requirements: NormalizedRequirement = Field(description="Normalized and validated requirements object")
    missing_fields: List[str] = Field(default_factory=list, description="Fields not mentioned by user (returned as null)")
    assumptions: List[str] = Field(default_factory=list, description="Documented assumptions applied during analysis")
    is_complete: bool = Field(default=False, description="Whether all core fields needed for architecture evaluation are present")
    raw_input: Optional[str] = Field(default=None, description="Original natural-language input or form payload")

