import logging
from typing import Dict, Any, List, Set, Optional, Tuple
import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [Anshika-LeakageGuard] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("ADIP_LeakageGuard")


class LeakageGuard:
    """
    Leakage detection and contamination defense engine implementing Phase 4 Section 7:
      7.1 Target Leakage Detection (Per-model target & outcome segregation)
      7.2 Feature Leakage & 3-Tier Feature Classification (User-supplied vs Derived vs Outcomes)
      7.3 Temporal Leakage Checks (Chronological partition validation)
      7.4 Train/Test Contamination Checks (Grouped architecture isolation & duplicate containment)
    """

    # 7.2 Strict 3-Tier Feature Classification
    FEATURE_TIERS = {
        "USER_SUPPLIED": [
            "domain", "users", "rps", "peak_rps", "concurrency",
            "data_size", "read_write_ratio", "request_size",
            "latency_sla", "availability_sla", "budget", "traffic_growth",
            "team_size"
        ],
        "DERIVED_STRUCTURAL": [
            "architecture_pattern", "architecture_style", "database",
            "cache", "messaging", "api_style", "deployment", "cloud",
            "service_count", "replica_count", "cpu_limit", "memory_limit",
            "node_count", "edge_count", "graph_depth", "average_degree",
            "max_fan_in", "max_fan_out", "critical_path_length",
            "architecture_complexity_score", "rps_per_service",
            "concurrency_per_replica", "data_per_request_ratio",
            "cache_capacity_coverage", "workload_type", "traffic_pattern"
        ],
        "OBSERVED_OUTCOMES": [
            # Latency outcomes
            "p50", "p90", "p95", "p99", "mean_latency", "db_latency",
            "network_latency_ms", "observed_cache_hit_rate",
            # Throughput outcomes
            "throughput", "actual_rps", "error_rate", "failed_requests",
            # Resource outcomes
            "cpu_utilization_ratio", "memory_utilization_ratio",
            "observed_cpu_pct", "observed_memory_mb", "disk_io_iops",
            # Cost outcomes
            "total_monthly_cost", "monthly_cost", "compute_cost",
            "database_cost", "cache_cost", "storage_cost", "network_cost",
            "managed_services_cost", "cost_per_100k_reqs",
            # Reliability & Scalability outcomes
            "availability_score", "sla_violation", "saturation_point_observed_rps",
            "observed_error_rate_pct"
        ]
    }

    # 7.1 Prohibited features per target model
    PROHIBITED_PER_TARGET: Dict[str, List[str]] = {
        "p99": [
            "p50", "p90", "p95", "p99", "mean_latency", "db_latency",
            "network_latency_ms", "observed_cache_hit_rate", "throughput",
            "error_rate", "cpu_utilization_ratio", "memory_utilization_ratio"
        ],
        "throughput": [
            "throughput", "actual_rps", "error_rate", "failed_requests",
            "p50", "p90", "p95", "p99", "mean_latency", "db_latency"
        ],
        "total_monthly_cost": [
            "total_monthly_cost", "monthly_cost", "compute_cost", "database_cost",
            "cache_cost", "storage_cost", "network_cost", "managed_services_cost",
            "cost_per_100k_reqs"
        ],
        "monthly_cost": [
            "total_monthly_cost", "monthly_cost", "compute_cost", "database_cost",
            "cache_cost", "storage_cost", "network_cost", "managed_services_cost"
        ],
        "availability_score": [
            "availability_score", "sla_violation", "error_rate", "failed_requests"
        ],
        "scalability_headroom_multiplier": [
            "saturation_point_observed_rps", "throughput", "actual_rps"
        ]
    }

    def __init__(self):
        logger.info("LeakageGuard initialized successfully.")

    # 7.2 Feature Classification Audit
    def classify_feature(self, feature_name: str) -> str:
        """Categorizes a feature into User-Supplied, Derived-Structural, or Observed-Outcome."""
        for tier, features in self.FEATURE_TIERS.items():
            if feature_name in features:
                return tier
        return "UNKNOWN_UNCLASSIFIED"

    def audit_feature_matrix_tier_compliance(
        self,
        candidate_feature_columns: List[str]
    ) -> Dict[str, Any]:
        """
        Validates that NO observed runtime outcomes exist in candidate input feature set X.
        Observed outcomes are only available after a system is built and run, so using them
        at recommendation time is catastrophic feature leakage.
        """
        leaked_outcomes = []
        user_supplied = []
        derived_structural = []
        unclassified = []

        for col in candidate_feature_columns:
            tier = self.classify_feature(col)
            if tier == "OBSERVED_OUTCOMES":
                leaked_outcomes.append(col)
            elif tier == "USER_SUPPLIED":
                user_supplied.append(col)
            elif tier == "DERIVED_STRUCTURAL":
                derived_structural.append(col)
            else:
                unclassified.append(col)

        passed = len(leaked_outcomes) == 0
        return {
            "check": "7.2_feature_tier_compliance",
            "passed": passed,
            "total_features": len(candidate_feature_columns),
            "leaked_observed_outcomes_count": len(leaked_outcomes),
            "leaked_observed_outcomes": leaked_outcomes,
            "user_supplied_count": len(user_supplied),
            "derived_structural_count": len(derived_structural),
            "unclassified_count": len(unclassified),
            "issues": [
                f"Feature Leakage Detected: '{col}' is an observed outcome and MUST NOT be an input feature."
                for col in leaked_outcomes
            ]
        }

    # 7.1 Target Leakage Detection
    def audit_target_leakage(
        self,
        candidate_features: List[str],
        target_name: str
    ) -> Dict[str, Any]:
        """
        Verifies that no restatements, components, or direct consequences of the target
        appear in the feature matrix for a specific prediction surrogate model.
        """
        prohibited_list = self.PROHIBITED_PER_TARGET.get(target_name, [target_name])
        detected_leaks = [f for f in candidate_features if f in prohibited_list]
        passed = len(detected_leaks) == 0

        issues = []
        if not passed:
            for leak in detected_leaks:
                issues.append(
                    f"Target Leakage Alert: Feature '{leak}' is prohibited when predicting '{target_name}'. "
                    "It derives directly from or restates the target outcome."
                )

        return {
            "check": "7.1_target_leakage",
            "passed": passed,
            "target": target_name,
            "prohibited_features_count": len(prohibited_list),
            "detected_leaks_count": len(detected_leaks),
            "detected_leaks": detected_leaks,
            "issues": issues
        }

    # 7.4 Train/Test Contamination Checks
    def audit_train_test_contamination(
        self,
        train_df: pd.DataFrame,
        test_df: pd.DataFrame,
        val_df: Optional[pd.DataFrame] = None,
        group_col: str = "architecture_id",
        config_cols: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Verifies that no architecture ID, experiment ID, or duplicate configuration
        crosses the train/val/test split boundary.
        """
        train_groups = set(train_df[group_col].dropna().unique()) if group_col in train_df.columns else set()
        test_groups = set(test_df[group_col].dropna().unique()) if group_col in test_df.columns else set()
        val_groups = (
            set(val_df[group_col].dropna().unique())
            if val_df is not None and group_col in val_df.columns
            else set()
        )

        overlap_train_test = train_groups.intersection(test_groups)
        overlap_train_val = train_groups.intersection(val_groups)
        overlap_val_test = val_groups.intersection(test_groups)

        issues = []
        if len(overlap_train_test) > 0:
            issues.append(
                f"Contamination Detected: {len(overlap_train_test)} '{group_col}' keys overlap between Train and Test splits!"
            )
        if len(overlap_train_val) > 0:
            issues.append(
                f"Contamination Detected: {len(overlap_train_val)} '{group_col}' keys overlap between Train and Validation splits!"
            )
        if len(overlap_val_test) > 0:
            issues.append(
                f"Contamination Detected: {len(overlap_val_test)} '{group_col}' keys overlap between Validation and Test splits!"
            )

        # Config-level duplicate check across train and test
        default_config_cols = [
            "architecture_pattern", "database", "cache", "messaging",
            "deployment", "cloud", "rps", "concurrency"
        ]
        active_config_cols = [c for c in (config_cols or default_config_cols) if c in train_df.columns and c in test_df.columns]
        config_overlap_count = 0

        if len(active_config_cols) >= 3:
            train_configs = train_df[active_config_cols].drop_duplicates()
            test_configs = test_df[active_config_cols].drop_duplicates()
            merged_configs = pd.merge(train_configs, test_configs, on=active_config_cols, how="inner")
            config_overlap_count = len(merged_configs)
            if config_overlap_count > 0:
                issues.append(
                    f"Near-Duplicate Contamination: {config_overlap_count} identical configurations span both Train and Test. "
                    "GroupShuffleSplit must group on composite configuration hash."
                )

        passed = len(overlap_train_test) == 0 and len(overlap_train_val) == 0 and config_overlap_count == 0

        return {
            "check": "7.4_train_test_contamination",
            "passed": passed,
            "group_column": group_col,
            "train_unique_groups": len(train_groups),
            "val_unique_groups": len(val_groups),
            "test_unique_groups": len(test_groups),
            "overlap_train_test_count": len(overlap_train_test),
            "overlap_train_val_count": len(overlap_train_val),
            "config_overlap_count": config_overlap_count,
            "issues": issues
        }

    # 7.3 Temporal Leakage Checks
    def audit_temporal_leakage(
        self,
        train_df: pd.DataFrame,
        test_df: pd.DataFrame,
        timestamp_col: str = "collection_timestamp"
    ) -> Dict[str, Any]:
        """
        Verifies that for time-series traces (e.g. Alibaba cluster telemetry),
        training periods strictly precede evaluation periods.
        """
        if timestamp_col not in train_df.columns or timestamp_col not in test_df.columns:
            return {
                "check": "7.3_temporal_leakage",
                "passed": True,
                "status": "SKIPPED_NO_TIMESTAMP_COLUMN",
                "issues": []
            }

        train_ts = pd.to_datetime(train_df[timestamp_col], errors="coerce").dropna()
        test_ts = pd.to_datetime(test_df[timestamp_col], errors="coerce").dropna()

        if len(train_ts) == 0 or len(test_ts) == 0:
            return {
                "check": "7.3_temporal_leakage",
                "passed": True,
                "status": "SKIPPED_EMPTY_TIMESTAMPS",
                "issues": []
            }

        max_train = train_ts.max()
        min_test = test_ts.min()
        passed = max_train <= min_test

        issues = []
        if not passed:
            issues.append(
                f"Temporal Leakage Alert: Training split maximum timestamp ({max_train}) "
                f"is later than Test split minimum timestamp ({min_test}). Model is learning from the future!"
            )

        return {
            "check": "7.3_temporal_leakage",
            "passed": passed,
            "max_train_timestamp": str(max_train),
            "min_test_timestamp": str(min_test),
            "is_strictly_chronological": passed,
            "issues": issues
        }

    # Comprehensive Leakage Audit Suite
    def run_full_leakage_audit(
        self,
        candidate_features: List[str],
        target_name: str,
        train_df: Optional[pd.DataFrame] = None,
        test_df: Optional[pd.DataFrame] = None,
        val_df: Optional[pd.DataFrame] = None,
        group_col: str = "architecture_id",
        timestamp_col: Optional[str] = "collection_timestamp"
    ) -> Dict[str, Any]:
        """
        Executes all Section 7 leakage detection checks:
          - Target leakage
          - Feature matrix tier compliance
          - Train/Test contamination
          - Temporal ordering
        """
        logger.info(f"Running full leakage audit for target '{target_name}' across {len(candidate_features)} candidate features.")

        tier_res = self.audit_feature_matrix_tier_compliance(candidate_features)
        target_res = self.audit_target_leakage(candidate_features, target_name)

        contam_res = {"passed": True, "status": "SKIPPED_NO_DATAFRAMES", "issues": []}
        temporal_res = {"passed": True, "status": "SKIPPED_NO_DATAFRAMES", "issues": []}

        if train_df is not None and test_df is not None:
            contam_res = self.audit_train_test_contamination(
                train_df=train_df,
                test_df=test_df,
                val_df=val_df,
                group_col=group_col
            )
            if timestamp_col:
                temporal_res = self.audit_temporal_leakage(
                    train_df=train_df,
                    test_df=test_df,
                    timestamp_col=timestamp_col
                )

        all_checks = [tier_res, target_res, contam_res, temporal_res]
        all_passed = all(c.get("passed", False) for c in all_checks)

        all_issues = []
        for c in all_checks:
            all_issues.extend(c.get("issues", []))

        audit_summary = {
            "phase": "Phase 4 - Leakage Prevention",
            "lead": "Anshika",
            "is_leakage_free": all_passed,
            "overall_status": "APPROVED_LEAKAGE_FREE" if all_passed else "LEAKAGE_DETECTED",
            "target_model": target_name,
            "summary": {
                "feature_tier_compliant": tier_res["passed"],
                "target_leakage_free": target_res["passed"],
                "contamination_free": contam_res["passed"],
                "temporal_ordering_valid": temporal_res["passed"],
            },
            "total_issues_identified": len(all_issues),
            "issues": all_issues,
            "detailed_reports": {
                "feature_tiers": tier_res,
                "target_leakage": target_res,
                "contamination": contam_res,
                "temporal_ordering": temporal_res,
            }
        }

        logger.info(
            f"Leakage Audit Complete: Status={audit_summary['overall_status']} | "
            f"Total Issues={len(all_issues)}"
        )
        return audit_summary


if __name__ == "__main__":
    # Self-test using sample feature lists and partitions
    guard = LeakageGuard()

    # Test 1: Valid candidate features for p99 latency prediction
    valid_features = [
        "domain", "rps", "concurrency", "read_write_ratio",
        "architecture_pattern", "database", "cache", "service_count",
        "graph_depth", "max_fan_out", "architecture_complexity_score"
    ]
    res_valid = guard.run_full_leakage_audit(valid_features, target_name="p99")
    print(f"Test 1 (Valid Features) Status: {res_valid['overall_status']}")

    # Test 2: Leaky candidate features (including p50 and throughput)
    leaky_features = valid_features + ["p50", "throughput", "cpu_utilization_ratio"]
    res_leaky = guard.run_full_leakage_audit(leaky_features, target_name="p99")
    print(f"Test 2 (Leaky Features) Status: {res_leaky['overall_status']} (Issues: {res_leaky['total_issues_identified']})")
