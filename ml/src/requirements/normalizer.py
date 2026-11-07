import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from ml.src.requirements.schemas import (
    NormalizedRequirement,
    RawExtractedRequirements,
    DomainType,
    WorkloadType,
)

logger = logging.getLogger("ADIP_RequirementNormalizer")


class RequirementNormalizer:
    """
    Phase 5 Lead Deliverable — Anshika (AI/ML & Intelligence Lead)
    Implements Table 4 & Section 6.4 normalization rules from Phase 5 specification:
      - Unit and format conversions (millions, 'k', lakh, crore, percentages)
      - Domain mapping to controlled vocabulary (e.g. 'online shop' -> 'ecommerce')
      - Storage standardization to Gigabytes (GB)
      - High-availability 'nines' conversion ('four nines' -> 99.99)
      - Read/write ratio parsing ('80/20 read/write' -> 0.8)
      - Missing field tracking without silent invention
    """

    # Domain Synonyms Map -> Controlled Vocabulary
    DOMAIN_SYNONYMS: Dict[str, str] = {
        # E-Commerce
        "online shop": DomainType.ECOMMERCE.value,
        "online shopping": DomainType.ECOMMERCE.value,
        "e-commerce": DomainType.ECOMMERCE.value,
        "ecommerce": DomainType.ECOMMERCE.value,
        "e commerce": DomainType.ECOMMERCE.value,
        "retail": DomainType.ECOMMERCE.value,
        "marketplace": DomainType.ECOMMERCE.value,
        "web store": DomainType.ECOMMERCE.value,
        "online store": DomainType.ECOMMERCE.value,
        # Fintech
        "fintech": DomainType.FINTECH.value,
        "banking": DomainType.FINTECH.value,
        "payments": DomainType.FINTECH.value,
        "payment gateway": DomainType.FINTECH.value,
        "crypto": DomainType.FINTECH.value,
        "financial": DomainType.FINTECH.value,
        "trading": DomainType.FINTECH.value,
        # Social Network
        "social network": DomainType.SOCIAL_NETWORK.value,
        "social media": DomainType.SOCIAL_NETWORK.value,
        "social": DomainType.SOCIAL_NETWORK.value,
        "community platform": DomainType.SOCIAL_NETWORK.value,
        # Streaming
        "streaming": DomainType.STREAMING.value,
        "video streaming": DomainType.STREAMING.value,
        "media": DomainType.STREAMING.value,
        "audio streaming": DomainType.STREAMING.value,
        "ott": DomainType.STREAMING.value,
        # IoT
        "iot": DomainType.IOT.value,
        "internet of things": DomainType.IOT.value,
        "smart home": DomainType.IOT.value,
        "telemetry": DomainType.IOT.value,
        "sensor network": DomainType.IOT.value,
        # Healthcare
        "healthcare": DomainType.HEALTHCARE.value,
        "medical": DomainType.HEALTHCARE.value,
        "hospital": DomainType.HEALTHCARE.value,
        "ehr": DomainType.HEALTHCARE.value,
        "telemedicine": DomainType.HEALTHCARE.value,
        # SaaS
        "saas": DomainType.SAAS.value,
        "b2b saas": DomainType.SAAS.value,
        "enterprise software": DomainType.SAAS.value,
        "cloud platform": DomainType.SAAS.value,
    }

    # Workload Type Synonyms Map
    WORKLOAD_SYNONYMS: Dict[str, str] = {
        "transactional": WorkloadType.TRANSACTIONAL.value,
        "oltp": WorkloadType.TRANSACTIONAL.value,
        "read heavy": WorkloadType.READ_HEAVY.value,
        "read-heavy": WorkloadType.READ_HEAVY.value,
        "read_heavy": WorkloadType.READ_HEAVY.value,
        "reads": WorkloadType.READ_HEAVY.value,
        "write heavy": WorkloadType.WRITE_HEAVY.value,
        "write-heavy": WorkloadType.WRITE_HEAVY.value,
        "write_heavy": WorkloadType.WRITE_HEAVY.value,
        "writes": WorkloadType.WRITE_HEAVY.value,
        "balanced": WorkloadType.BALANCED.value,
        "mixed": WorkloadType.BALANCED.value,
        "streaming": WorkloadType.STREAMING.value,
        "real-time": WorkloadType.STREAMING.value,
        "event-driven": WorkloadType.STREAMING.value,
        "analytical": WorkloadType.ANALYTICAL.value,
        "olap": WorkloadType.ANALYTICAL.value,
    }

    # Availability SLA "nines" lookup
    NINES_MAP: Dict[str, float] = {
        "two nines": 99.0,
        "three nines": 99.9,
        "four nines": 99.99,
        "five nines": 99.999,
        "six nines": 99.9999,
    }

    def __init__(self):
        logger.info("RequirementNormalizer initialized successfully.")

    # -------------------------------------------------------------------------
    # Number & Scale Normalizers (millions, k, lakh, crore)
    # -------------------------------------------------------------------------
    @staticmethod
    def normalize_number(raw: Any) -> Optional[float]:
        """
        Parses numeric expressions with scale words into canonical floats/ints:
          - '5 million' / '5M' -> 5,000,000
          - '50k' / '5k'       -> 50,000 / 5,000
          - '4 lakh' / '4 lac' -> 400,000
          - '1.5 crore' / '1 cr'-> 15,000,000
          - '10 billion' / '10B'-> 10,000,000,000
        """
        if raw is None:
            return None
        if isinstance(raw, (int, float)):
            return float(raw)

        s = str(raw).strip().lower().replace(",", "")

        # Extract multiplier keywords (handles attached '5M', '100k', '4lac' and spaced '5 million')
        multiplier = 1.0
        if re.search(r"(?<=\d)b\b|\bb\b|\bbillions?\b", s):
            multiplier = 1_000_000_000.0
        elif re.search(r"(?<=\d)cr\b|\bcr\b|\bcrores?\b", s):
            multiplier = 10_000_000.0
        elif re.search(r"(?<=\d)m\b|\bm\b|\bmillions?\b", s):
            multiplier = 1_000_000.0
        elif re.search(r"(?<=\d)lakhs?\b|\blakhs?\b|(?<=\d)lacs?\b|\blacs?\b", s):
            multiplier = 100_000.0
        elif re.search(r"(?<=\d)k\b|\bk\b|\bthousands?\b", s):
            multiplier = 1_000.0

        # Extract numeric base
        match = re.search(r"[-+]?\d*\.?\d+", s)
        if match:
            try:
                base_val = float(match.group())
                return base_val * multiplier
            except ValueError:
                return None
        return None

    # -------------------------------------------------------------------------
    # Rate Normalizer (RPS, req/sec, req/min, req/day)
    # -------------------------------------------------------------------------
    @classmethod
    def normalize_rps(cls, raw: Any) -> Optional[float]:
        """
        Standardizes rate expressions to Requests Per Second (RPS):
          - '5,000 RPS' / '5k requests per second' -> 5000.0
          - '60,000 requests per minute' -> 1000.0
          - '864,000 requests per day' -> 10.0
        """
        if raw is None:
            return None
        if isinstance(raw, (int, float)):
            return float(raw)

        s = str(raw).strip().lower().replace(",", "")

        # Check for time-denominator units
        divisor = 1.0
        if re.search(r"\bper minute\b|\b/min\b|\bpm\b", s):
            divisor = 60.0
        elif re.search(r"\bper day\b|\b/day\b|\b/d\b", s):
            divisor = 86400.0
        elif re.search(r"\bper hour\b|\b/hour\b|\b/hr\b", s):
            divisor = 3600.0

        base_val = cls.normalize_number(s)
        if base_val is not None:
            return round(base_val / divisor, 2)
        return None

    # -------------------------------------------------------------------------
    # Currency / Budget Normalizer (INR, USD, Lakhs)
    # -------------------------------------------------------------------------
    @classmethod
    def normalize_budget(cls, raw: Any) -> Optional[float]:
        """
        Table 4: '₹4 lakh per month' -> 400000.0
        Extracts monetary budget value in canonical numeric units.
        """
        if raw is None:
            return None
        if isinstance(raw, (int, float)):
            return float(raw)

        s = str(raw).strip().lower().replace(",", "")
        # Remove currency symbols for number extraction
        cleaned = re.sub(r"[₹$€£usd|inr|rs\.?]", "", s).strip()
        num_val = cls.normalize_number(cleaned)
        return num_val

    # -------------------------------------------------------------------------
    # Availability SLA Normalizer ('four nines', 99.99%)
    # -------------------------------------------------------------------------
    @classmethod
    def normalize_availability(cls, raw: Any) -> Optional[float]:
        """
        Table 4: 'four nines' / '99.99% uptime' -> 99.99
        Standardizes uptime percentage between 90.0 and 100.0.
        """
        if raw is None:
            return None
        if isinstance(raw, (int, float)):
            val = float(raw)
            # If written as fraction 0.9999 -> convert to 99.99
            if 0.90 <= val <= 1.0:
                val = val * 100.0
            return round(val, 4)

        s = str(raw).strip().lower()

        # Check textual 'nines'
        for text_nines, val in cls.NINES_MAP.items():
            if text_nines in s:
                return val

        # Check percentage string '99.99%'
        match = re.search(r"[-+]?\d*\.?\d+", s)
        if match:
            try:
                val = float(match.group())
                if 0.90 <= val <= 1.0:
                    val = val * 100.0
                return round(val, 4)
            except ValueError:
                return None
        return None

    # -------------------------------------------------------------------------
    # Domain Category Normalizer ('online shop' -> 'ecommerce')
    # -------------------------------------------------------------------------
    @classmethod
    def normalize_domain(cls, raw: Any) -> Optional[str]:
        """
        Table 4: 'online shop' / 'e-commerce' -> 'ecommerce'
        Maps raw terms to controlled domain vocabulary.
        """
        if not raw:
            return None

        s = str(raw).strip().lower()
        if s in cls.DOMAIN_SYNONYMS:
            return cls.DOMAIN_SYNONYMS[s]

        # Partial matching check
        for phrase, canonical in cls.DOMAIN_SYNONYMS.items():
            if phrase in s or s in phrase:
                return canonical

        return DomainType.OTHER.value

    # -------------------------------------------------------------------------
    # Workload Type Normalizer ('transactional', 'read-heavy')
    # -------------------------------------------------------------------------
    @classmethod
    def normalize_workload_type(cls, raw: Any) -> Optional[str]:
        """Standardizes workload profile to controlled vocabulary."""
        if not raw:
            return None

        s = str(raw).strip().lower()

        # Direct enum value match
        for wt in WorkloadType:
            if s == wt.value:
                return wt.value

        if s in cls.WORKLOAD_SYNONYMS:
            return cls.WORKLOAD_SYNONYMS[s]

        cleaned_s = s.replace("_", " ").replace("-", " ")
        if cleaned_s in cls.WORKLOAD_SYNONYMS:
            return cls.WORKLOAD_SYNONYMS[cleaned_s]

        for phrase, canonical in cls.WORKLOAD_SYNONYMS.items():
            if phrase in s or phrase in cleaned_s:
                return canonical

        return WorkloadType.BALANCED.value

    # -------------------------------------------------------------------------
    # Data Storage Normalizer (GB canonical: TB, MB, PB -> GB)
    # -------------------------------------------------------------------------
    @classmethod
    def normalize_data_size(cls, raw: Any) -> Optional[float]:
        """Standardizes storage volume into Gigabytes (GB)."""
        if raw is None:
            return None
        if isinstance(raw, (int, float)):
            return float(raw)

        s = str(raw).strip().lower().replace(",", "")

        multiplier = 1.0  # Default GB
        if re.search(r"\bpb\b|\bpetabyte\b", s):
            multiplier = 1024.0 * 1024.0
        elif re.search(r"\btb\b|\bterabyte\b", s):
            multiplier = 1024.0
        elif re.search(r"\bmb\b|\bmegabyte\b", s):
            multiplier = 1.0 / 1024.0
        elif re.search(r"\bkb\b|\bkilobyte\b", s):
            multiplier = 1.0 / (1024.0 * 1024.0)

        match = re.search(r"[-+]?\d*\.?\d+", s)
        if match:
            try:
                base_num = float(match.group())
                return round(base_num * multiplier, 2)
            except ValueError:
                return None
        return None

    # -------------------------------------------------------------------------
    # Read/Write Ratio Normalizer ('80/20 read/write' -> 0.80)
    # -------------------------------------------------------------------------
    @staticmethod
    def normalize_read_write_ratio(raw: Any) -> Optional[float]:
        """
        Parses read-heavy fractions into canonical read ratios in [0.0, 1.0]:
          - '80/20' / '80:20' / '80/20 read/write' -> 0.80
          - '90% reads' -> 0.90
        """
        if raw is None:
            return None
        if isinstance(raw, (int, float)):
            val = float(raw)
            if val > 1.0 and val <= 100.0:
                val = val / 100.0
            return round(val, 2)

        s = str(raw).strip().lower()

        # Ratio format '80/20' or '80:20'
        ratio_match = re.search(r"(\d+)\s*[/:]\s*(\d+)", s)
        if ratio_match:
            reads = float(ratio_match.group(1))
            writes = float(ratio_match.group(2))
            total = reads + writes
            if total > 0:
                return round(reads / total, 2)

        # Percentage format '90% reads' or '80% read'
        pct_match = re.search(r"(\d+(?:\.\d+)?)\s*%", s)
        if pct_match:
            val = float(pct_match.group(1)) / 100.0
            return round(val, 2)

        # Plain number string '0.8'
        num_match = re.search(r"[-+]?\d*\.?\d+", s)
        if num_match:
            val = float(num_match.group())
            if val > 1.0 and val <= 100.0:
                val = val / 100.0
            return round(val, 2)

        return None

    # -------------------------------------------------------------------------
    # Latency SLA Normalizer ('15ms' -> 15.0)
    # -------------------------------------------------------------------------
    @staticmethod
    def normalize_latency_sla(raw: Any) -> Optional[float]:
        """Standardizes latency limit into milliseconds (ms)."""
        if raw is None:
            return None
        if isinstance(raw, (int, float)):
            return float(raw)

        s = str(raw).strip().lower()
        multiplier = 1.0  # Default ms
        if re.search(r"\bseconds?\b|\bs\b", s) and not re.search(r"\bms\b|\bmillis", s):
            multiplier = 1000.0

        match = re.search(r"[-+]?\d*\.?\d+", s)
        if match:
            try:
                base_num = float(match.group())
                return round(base_num * multiplier, 2)
            except ValueError:
                return None
        return None

    # -------------------------------------------------------------------------
    # End-to-End Requirement Normalization Engine
    # -------------------------------------------------------------------------
    @classmethod
    def normalize_requirements(
        cls,
        raw_input: Dict[str, Any] | RawExtractedRequirements,
        project_id: Optional[str] = None
    ) -> Tuple[NormalizedRequirement, List[str], List[str]]:
        """
        Normalizes raw inputs and tracks missing fields and flagged assumptions:
          - Fields unmentioned are returned as None (null) and listed in missing_fields.
          - Never silently invents unmentioned parameters.
          - Documented assumptions (e.g., peak multiplier) are flagged explicitly.
        """
        if isinstance(raw_input, RawExtractedRequirements):
            data = raw_input.model_dump()
        else:
            data = dict(raw_input)

        norm_data: Dict[str, Any] = {"project_id": project_id}
        missing_fields: List[str] = []
        assumptions: List[str] = []

        # 1. Domain
        domain_raw = data.get("domain")
        if domain_raw is not None:
            norm_data["domain"] = cls.normalize_domain(domain_raw)
        else:
            missing_fields.append("domain")

        # 2. Users
        users_raw = data.get("users")
        if users_raw is not None:
            norm_num = cls.normalize_number(users_raw)
            norm_data["users"] = int(norm_num) if norm_num is not None else None
        else:
            missing_fields.append("users")

        # 3. Concurrency
        conc_raw = data.get("concurrency")
        if conc_raw is not None:
            norm_conc = cls.normalize_number(conc_raw)
            norm_data["concurrency"] = int(norm_conc) if norm_conc is not None else None
        else:
            missing_fields.append("concurrency")

        # 4. RPS
        rps_raw = data.get("rps")
        if rps_raw is not None:
            norm_data["rps"] = cls.normalize_rps(rps_raw)
        else:
            missing_fields.append("rps")

        # 5. Peak RPS
        peak_raw = data.get("peak_rps")
        if peak_raw is not None:
            norm_data["peak_rps"] = cls.normalize_rps(peak_raw)
        else:
            missing_fields.append("peak_rps")
            # If baseline RPS is available, document peak multiplier assumption
            if norm_data.get("rps"):
                assumed_peak = round(norm_data["rps"] * 2.0, 1)
                norm_data["peak_rps"] = assumed_peak
                assumptions.append(
                    f"Peak RPS was not specified; assumed a 2.0x peak multiplier ({assumed_peak} RPS) based on domain heuristic."
                )

        # 6. Data Size
        data_raw = data.get("data_size")
        if data_raw is not None:
            norm_data["data_size"] = cls.normalize_data_size(data_raw)
        else:
            missing_fields.append("data_size")

        # 7. Read/Write Ratio
        rw_raw = data.get("read_write_ratio")
        if rw_raw is not None:
            norm_data["read_write_ratio"] = cls.normalize_read_write_ratio(rw_raw)
        else:
            missing_fields.append("read_write_ratio")

        # 8. Latency SLA
        lat_raw = data.get("latency_sla")
        if lat_raw is not None:
            norm_data["latency_sla"] = cls.normalize_latency_sla(lat_raw)
        else:
            missing_fields.append("latency_sla")

        # 9. Availability SLA
        avail_raw = data.get("availability_sla")
        if avail_raw is not None:
            norm_data["availability_sla"] = cls.normalize_availability(avail_raw)
        else:
            missing_fields.append("availability_sla")

        # 10. Budget
        budget_raw = data.get("budget")
        if budget_raw is not None:
            norm_data["budget"] = cls.normalize_budget(budget_raw)
        else:
            missing_fields.append("budget")

        # 11. Traffic Growth
        growth_raw = data.get("traffic_growth")
        if growth_raw is not None:
            norm_data["traffic_growth"] = cls.normalize_number(growth_raw)
        else:
            missing_fields.append("traffic_growth")

        # 12. Team Size
        team_raw = data.get("team_size")
        if team_raw is not None:
            norm_team = cls.normalize_number(team_raw)
            norm_data["team_size"] = int(norm_team) if norm_team is not None else None
        else:
            missing_fields.append("team_size")

        # 13. Workload Type
        wl_raw = data.get("workload_type")
        if wl_raw is not None:
            norm_data["workload_type"] = cls.normalize_workload_type(wl_raw)
        else:
            missing_fields.append("workload_type")
            # Domain-based assumption if domain exists
            if norm_data.get("domain") == DomainType.ECOMMERCE.value:
                norm_data["workload_type"] = WorkloadType.TRANSACTIONAL.value
                assumptions.append("Workload type not specified; defaulted to 'transactional' based on e-commerce domain.")

        # Build validated Pydantic model
        validated_req = NormalizedRequirement(**norm_data)
        return validated_req, missing_fields, assumptions

        # 7. Read/Write Ratio
        rw_raw = data.get("read_write_ratio")
        if rw_raw is not None:
            norm_data["read_write_ratio"] = self.normalize_read_write_ratio(rw_raw)
        else:
            missing_fields.append("read_write_ratio")

        # 8. Latency SLA
        lat_raw = data.get("latency_sla")
        if lat_raw is not None:
            norm_data["latency_sla"] = self.normalize_latency_sla(lat_raw)
        else:
            missing_fields.append("latency_sla")

        # 9. Availability SLA
        avail_raw = data.get("availability_sla")
        if avail_raw is not None:
            norm_data["availability_sla"] = self.normalize_availability(avail_raw)
        else:
            missing_fields.append("availability_sla")

        # 10. Budget
        budget_raw = data.get("budget")
        if budget_raw is not None:
            norm_data["budget"] = self.normalize_budget(budget_raw)
        else:
            missing_fields.append("budget")

        # 11. Traffic Growth
        growth_raw = data.get("traffic_growth")
        if growth_raw is not None:
            norm_data["traffic_growth"] = self.normalize_number(growth_raw)
        else:
            missing_fields.append("traffic_growth")

        # 12. Team Size
        team_raw = data.get("team_size")
        if team_raw is not None:
            norm_team = self.normalize_number(team_raw)
            norm_data["team_size"] = int(norm_team) if norm_team is not None else None
        else:
            missing_fields.append("team_size")

        # 13. Workload Type
        wl_raw = data.get("workload_type")
        if wl_raw is not None:
            norm_data["workload_type"] = self.normalize_workload_type(wl_raw)
        else:
            missing_fields.append("workload_type")
            # Domain-based assumption if domain exists
            if norm_data.get("domain") == DomainType.ECOMMERCE.value:
                norm_data["workload_type"] = WorkloadType.TRANSACTIONAL.value
                assumptions.append("Workload type not specified; defaulted to 'transactional' based on e-commerce domain.")

        # Build validated Pydantic model
        validated_req = NormalizedRequirement(**norm_data)
        return validated_req, missing_fields, assumptions
