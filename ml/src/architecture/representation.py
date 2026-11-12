import logging
from typing import Dict, Any, Optional, List, Tuple, Union
import numpy as np
import pandas as pd

from ml.src.features.feature_registry import (
    CATEGORICAL_FEATURES,
    BASE_NUMERICAL_FEATURES,
    GRAPH_TOPOLOGY_FEATURES,
    INTERACTION_FEATURES,
    ALL_FEATURE_COLUMNS,
    MODEL_TARGETS,
)
from ml.src.requirements.schemas import NormalizedRequirement
from ml.src.architecture.schemas import ArchitectureGraph
from ml.src.architecture.graph_extractor import ArchitectureGraphExtractor

logger = logging.getLogger("ADIP_MLRepresentation")


class MLArchitectureRepresentation:
    """
    Unified representation engine for converting raw architecture graphs
    and Phase 5 requirement specifications into validated, ML-ready feature vectors.
    """

    ENCODER_VERSION = "1.0.0"

    def __init__(self):
        logger.info(f"Initialized MLArchitectureRepresentation (version {self.ENCODER_VERSION}).")
        self.categorical_vocab = CATEGORICAL_FEATURES
        self.all_columns = ALL_FEATURE_COLUMNS


    def build_feature_dict(
        self,
        architecture: Union[ArchitectureGraph, Dict[str, Any]],
        requirements: Optional[Union[NormalizedRequirement, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Extracts architecture features and fuses them with Phase 5 requirements,
        calculating intensity interactions and enforcing zero target leakage.
        """
        # 1. Extract architecture features (graph topology + component stats)
        arch_features = ArchitectureGraphExtractor.extract_features(architecture)

        # 2. Extract requirement / workload parameters
        req_data: Dict[str, Any] = {}
        if isinstance(requirements, NormalizedRequirement):
            req_data = requirements.model_dump()
        elif isinstance(requirements, dict):
            req_data = dict(requirements)

        # Workload dimensions with safe defaults
        rps = float(req_data.get("rps") or req_data.get("peak_rps") or 100.0)
        concurrency = float(req_data.get("concurrency") or (rps * 0.5) or 50.0)
        read_write_ratio = float(req_data.get("read_write_ratio") or 0.8)
        data_size = float(req_data.get("data_size") or 10.0)
        request_size = float(req_data.get("request_size") or 2.0)  # KB default
        workload_type = str(req_data.get("workload_type") or "balanced").lower()
        if workload_type == "transactional":
            workload_type = "oltp"

        traffic_pattern = str(req_data.get("traffic_pattern") or "steady").lower()

        # 3. Compute interaction features
        service_count = max(int(arch_features.get("service_count", 1)), 1)
        replica_count = max(int(arch_features.get("replica_count", 1)), 1)
        cache_tech = str(arch_features.get("cache", "none")).lower()

        rps_per_service = round(rps / float(service_count), 2)
        concurrency_per_replica = round(concurrency / float(replica_count), 2)
        data_per_request_ratio = round((data_size * 1024.0) / max(rps, 1.0), 3)
        cache_capacity_coverage = 0.0 if cache_tech in ["none", "", "null"] else 1.0

        # Assemble unified feature dictionary
        unified: Dict[str, Any] = {
            # Categoricals (10)
            "architecture_pattern": str(arch_features.get("architecture_pattern", "microservices")).lower(),
            "architecture_style": str(arch_features.get("architecture_style", "hexagonal")).lower(),
            "database": str(arch_features.get("database", "postgres")).lower(),
            "cache": cache_tech,
            "messaging": str(arch_features.get("messaging", "none")).lower(),
            "api_style": str(arch_features.get("api_style", "rest")).lower(),
            "deployment": str(arch_features.get("deployment", "kubernetes")).lower(),
            "cloud": str(arch_features.get("cloud", "aws")).lower(),
            "workload_type": workload_type,
            "traffic_pattern": traffic_pattern,
            # Base Numerical Dimensions (11)
            "service_count": service_count,
            "replica_count": replica_count,
            "cpu_limit": float(arch_features.get("cpu_limit", 1.0)),
            "memory_limit": float(arch_features.get("memory_limit", 2.0)),
            "node_count": int(arch_features.get("node_count", service_count)),
            "edge_count": int(arch_features.get("edge_count", 0)),
            "rps": rps,
            "concurrency": concurrency,
            "read_write_ratio": read_write_ratio,
            "data_size": data_size,
            "request_size": request_size,
            # Graph Topology Features (6)
            "graph_depth": int(arch_features.get("graph_depth", 1)),
            "average_degree": float(arch_features.get("average_degree", 1.0)),
            "max_fan_in": int(arch_features.get("max_fan_in", 1)),
            "max_fan_out": int(arch_features.get("max_fan_out", 1)),
            "critical_path_length": float(arch_features.get("critical_path_length", 1.5)),
            "architecture_complexity_score": float(arch_features.get("architecture_complexity_score", 1.0)),
            # Interaction Features (4)
            "rps_per_service": rps_per_service,
            "concurrency_per_replica": concurrency_per_replica,
            "data_per_request_ratio": data_per_request_ratio,
            "cache_capacity_coverage": cache_capacity_coverage,
        }

        # 4. Zero Target Leakage Validation (Section 9.2)
        self._validate_leakage_absence(unified)

        return unified

    # 2. DataFrame Construction
    def build_feature_dataframe(
        self,
        architecture: Union[ArchitectureGraph, Dict[str, Any]],
        requirements: Optional[Union[NormalizedRequirement, Dict[str, Any]]] = None,
    ) -> pd.DataFrame:
        """
        Builds a single-row Pandas DataFrame strictly aligned with ALL_FEATURE_COLUMNS.
        """
        feature_dict = self.build_feature_dict(architecture, requirements)
        df = pd.DataFrame([feature_dict])
        # Reorder to guarantee exact column ordering
        return df[self.all_columns]

    # 3. Numeric Vector Encoding (Section 10.1 & Section 12)
    def encode_feature_vector(
        self,
        feature_dict: Dict[str, Any]
    ) -> np.ndarray:
        """
        Encodes the feature dictionary into a 1D NumPy array for Scikit-learn/XGBoost.
        Categorical features are mapped using fixed index lookup; unseen categories
        are safely assigned a fallback index (0) without breaking prediction.
        """
        vector: List[float] = []

        # 1. Encode Categoricals
        for cat_col, allowed_values in self.categorical_vocab.items():
            val = str(feature_dict.get(cat_col, "")).lower()
            if val in allowed_values:
                code = float(allowed_values.index(val))
            else:
                # Unseen category safety fallback (Section 12)
                logger.warning(f"Unseen category '{val}' for column '{cat_col}'; defaulting to index 0.")
                code = 0.0
            vector.append(code)

        # 2. Encode Numerical Features
        numerical_cols = BASE_NUMERICAL_FEATURES + GRAPH_TOPOLOGY_FEATURES + INTERACTION_FEATURES
        for num_col in numerical_cols:
            val = float(feature_dict.get(num_col, 0.0))
            vector.append(val)

        return np.array(vector, dtype=np.float32)

    @staticmethod
    def _validate_leakage_absence(features: Dict[str, Any]) -> None:
        """
        Strictly forbids measured runtime targets (latency, throughput, cost, errors)
        from entering the architecture feature representation.
        """
        forbidden_targets = [
            "latency", "throughput", "p50", "p95", "p99",
            "monthly_cost", "error_rate", "actual_cost", "observed_latency",
            "cache_hit_rate_measured", "cpu_measured", "memory_measured"
        ]
        for key in features.keys():
            if key.lower() in forbidden_targets:
                raise ValueError(
                    f"Target Leakage detected: Runtime target '{key}' cannot be used as an architecture feature."
                )
