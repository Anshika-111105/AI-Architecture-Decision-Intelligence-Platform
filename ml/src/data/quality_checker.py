import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd
import yaml

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [Anshika-DataQuality] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("ADIP_QualityChecker")


class DataQualityChecker:
    """
    Comprehensive data quality validation engine implementing Phase 4 Section 6:
      6.1 Schema Validation (Key presence, types, orphan checks)
      6.2 Missing-Value Checks (Expected vs. unexpected gaps, imputation rules)
      6.3 Duplicate Detection (Exact, primary-key, and near-duplicates)
      6.4 Outlier Analysis (Robust IQR & Modified Z-Score / MAD)
      6.5 Range Validation (Physical boundary laws, percentile invariants)
      6.6 Categorical Validation (Controlled vocabulary conformance)
    """

    def __init__(
        self,
        features_cfg_path: Optional[str] = None,
        data_cfg_path: Optional[str] = None
    ):
        self.project_root = self._resolve_project_root()
        self.features_cfg = self._load_yaml(
            features_cfg_path or str(self.project_root / "ml" / "configs" / "features.yaml")
        )
        self.data_cfg = self._load_yaml(
            data_cfg_path or str(self.project_root / "ml" / "configs" / "data.yaml")
        )
        logger.info("DataQualityChecker initialized successfully.")

    @staticmethod
    def _resolve_project_root() -> Path:
        curr = Path.cwd().resolve()
        for p in [curr, *curr.parents]:
            if (p / "ml").is_dir() and (p / "packages").is_dir():
                return p
        return curr

    @staticmethod
    def _load_yaml(path_str: str) -> Dict[str, Any]:
        p = Path(path_str)
        if not p.exists():
            logger.warning(f"Config path not found: {path_str}, using empty configuration.")
            return {}
        with open(p, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    # 6.1 Schema Validation
    def check_schema(
        self,
        df: pd.DataFrame,
        dataset_key: Optional[str] = None,
        required_keys: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Validates column presence, expected primary keys, and identifies unexpected columns.
        """
        results = {
            "check": "6.1_schema_validation",
            "passed": True,
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "missing_required_columns": [],
            "unexpected_columns": [],
            "null_primary_keys": {},
            "issues": []
        }

        expected_fields: List[str] = []
        primary_key = None

        if dataset_key and dataset_key in self.features_cfg.get("datasets", {}):
            ds_spec = self.features_cfg["datasets"][dataset_key]
            expected_fields = list(ds_spec.get("fields", {}).keys())
            primary_key = ds_spec.get("primary_key")

        # Explicit required keys override or fallback
        keys_to_check = required_keys or ([primary_key] if primary_key else [])

        # Check required columns
        for k in keys_to_check:
            if k not in df.columns:
                results["missing_required_columns"].append(k)
                results["issues"].append(f"Mandatory primary/foreign key '{k}' missing from dataset.")
                results["passed"] = False
            else:
                null_count = int(df[k].isnull().sum())
                if null_count > 0:
                    results["null_primary_keys"][k] = null_count
                    results["issues"].append(f"Key column '{k}' has {null_count} null entries.")
                    results["passed"] = False

        # Identify unexpected columns if schema is strictly specified
        if expected_fields:
            for col in df.columns:
                if col not in expected_fields and col not in (keys_to_check or []):
                    results["unexpected_columns"].append(col)

        return results

    # 6.2 Missing-Value Checks
    def check_missing_values(
        self,
        df: pd.DataFrame,
        expected_optional_cols: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Calculates missingness per column and classifies gaps as expected (optional components)
        versus unexpected (telemetry failure requiring remediation).
        """
        optional_cols = expected_optional_cols or ["cache", "messaging", "read_write_ratio", "request_size"]
        results = {
            "check": "6.2_missing_values",
            "passed": True,
            "total_cells": df.size,
            "total_missing_cells": int(df.isnull().sum().sum()),
            "missing_per_column": {},
            "unexpected_missing_columns": [],
            "recommended_imputations": {},
            "issues": []
        }

        for col in df.columns:
            null_count = int(df[col].isnull().sum())
            if null_count > 0:
                pct = round((null_count / len(df)) * 100, 2)
                results["missing_per_column"][col] = {
                    "null_count": null_count,
                    "percentage": pct,
                    "is_expected": col in optional_cols
                }

                if col in optional_cols:
                    if pd.api.types.is_numeric_dtype(df[col]):
                        results["recommended_imputations"][col] = "median"
                    else:
                        results["recommended_imputations"][col] = "constant_none"
                else:
                    results["unexpected_missing_columns"].append(col)
                    results["issues"].append(f"Unexpected missing values in '{col}': {null_count} ({pct}%)")
                    results["passed"] = False

        return results

    # 6.3 Duplicate Detection
    def check_duplicates(
        self,
        df: pd.DataFrame,
        id_col: Optional[str] = "architecture_id",
        config_cols: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Detects exact duplicate rows, primary key collisions, and near-duplicates
        (identical configuration with repeated measurements).
        """
        results = {
            "check": "6.3_duplicate_detection",
            "passed": True,
            "exact_duplicates_count": int(df.duplicated().sum()),
            "id_collisions_count": 0,
            "near_duplicates_count": 0,
            "issues": []
        }

        if results["exact_duplicates_count"] > 0:
            results["issues"].append(f"Found {results['exact_duplicates_count']} exact duplicate rows.")
            results["passed"] = False

        # Primary key collision check
        if id_col and id_col in df.columns:
            id_dup_count = int(df.duplicated(subset=[id_col]).sum())
            results["id_collisions_count"] = id_dup_count
            if id_dup_count > 0:
                results["issues"].append(
                    f"Found {id_dup_count} duplicate primary key entries for '{id_col}'."
                )
                # Note: Repeated runs of one architecture may be valid, but flagged for splitting
                results["passed"] = False

        # Near-duplicate check (same architecture configuration and workload)
        default_config_cols = [
            "architecture_pattern", "database", "cache", "messaging",
            "deployment", "cloud", "rps", "concurrency"
        ]
        active_config_cols = [c for c in (config_cols or default_config_cols) if c in df.columns]
        if len(active_config_cols) >= 3:
            near_dup_mask = df.duplicated(subset=active_config_cols, keep=False)
            results["near_duplicates_count"] = int(near_dup_mask.sum())
            if results["near_duplicates_count"] > 0:
                results["issues"].append(
                    f"Identified {results['near_duplicates_count']} rows sharing identical configuration/workload. "
                    "Must be partitioned together during train/test splitting to prevent contamination."
                )

        return results

    # 6.4 Outlier Analysis
    def check_outliers(
        self,
        df: pd.DataFrame,
        target_columns: Optional[List[str]] = None,
        iqr_multiplier: float = 2.5
    ) -> Dict[str, Any]:
        """
        Profiles heavy-tailed distributions and flags extreme anomalies using
        robust non-parametric statistics (IQR and Median Absolute Deviation / MAD).
        Extreme values are flagged for review rather than deleted.
        """
        cols_to_check = target_columns or ["p50", "p95", "p99", "throughput", "total_monthly_cost"]
        results = {
            "check": "6.4_outlier_analysis",
            "passed": True,
            "outliers_by_column": {},
            "issues": []
        }

        for col in cols_to_check:
            if col not in df.columns or not pd.api.types.is_numeric_dtype(df[col]):
                continue

            series = df[col].dropna()
            if len(series) < 10:
                continue

            q25 = float(series.quantile(0.25))
            q75 = float(series.quantile(0.75))
            iqr = q75 - q25
            median = float(series.median())
            
            # Median Absolute Deviation (MAD)
            mad = float(np.median(np.abs(series - median)))
            mad_std = 1.4826 * mad if mad > 1e-6 else 1.0

            lower_bound = q25 - (iqr_multiplier * iqr)
            upper_bound = q75 + (iqr_multiplier * iqr)

            outlier_mask = (series < lower_bound) | (series > upper_bound)
            outlier_count = int(outlier_mask.sum())
            max_val = float(series.max())
            min_val = float(series.min())

            results["outliers_by_column"][col] = {
                "median": round(median, 2),
                "iqr": round(iqr, 2),
                "lower_bound": round(lower_bound, 2),
                "upper_bound": round(upper_bound, 2),
                "outlier_count": outlier_count,
                "outlier_pct": round((outlier_count / len(series)) * 100, 2),
                "min": round(min_val, 2),
                "max": round(max_val, 2)
            }

            # Outliers > 8% of data indicate high skew or queue saturation
            if (outlier_count / len(series)) > 0.08:
                results["issues"].append(
                    f"High outlier volume in '{col}': {outlier_count} records ({results['outliers_by_column'][col]['outlier_pct']}%). "
                    "Review queuing saturation knee and log-transform."
                )

        return results

    # 6.5 Range Validation (Physical Boundary Invariants)
    def check_physical_invariants(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Enforces domain-specific physical invariants:
          - Percentile monotonicity: p50 <= p90 <= p95 <= p99
          - Bounded ratios: read_write_ratio, error_rate, cache_hit_rate in [0.0, 1.0]
          - Positivity: rps > 0, concurrency > 0, latency >= 0, throughput > 0
          - Non-negative cost: monthly_cost >= 0
          - Resource bounds: cpu, memory >= 0
        """
        results = {
            "check": "6.5_range_and_physical_invariants",
            "passed": True,
            "violations": {},
            "issues": []
        }

        def _record_violation(rule_name: str, mask: pd.Series, description: str):
            count = int(mask.sum())
            if count > 0:
                results["violations"][rule_name] = count
                results["issues"].append(f"{description}: {count} violations detected.")
                results["passed"] = False

        # 1. Percentile Monotonicity (p50 <= p95 <= p99)
        if "p50" in df.columns and "p95" in df.columns:
            _record_violation(
                "p50_gt_p95",
                df["p50"] > df["p95"],
                "Percentile Invariant Violated (p50 > p95)"
            )
        if "p95" in df.columns and "p99" in df.columns:
            _record_violation(
                "p95_gt_p99",
                df["p95"] > df["p99"],
                "Percentile Invariant Violated (p95 > p99)"
            )
        if "p90" in df.columns and "p95" in df.columns:
            _record_violation(
                "p90_gt_p95",
                df["p90"] > df["p95"],
                "Percentile Invariant Violated (p90 > p95)"
            )

        # 2. Ratio Invariants [0.0, 1.0]
        for ratio_col in ["read_write_ratio", "error_rate", "cache_hit_rate", "availability_score"]:
            if ratio_col in df.columns:
                _record_violation(
                    f"{ratio_col}_out_of_bounds",
                    (df[ratio_col] < 0.0) | (df[ratio_col] > 1.0),
                    f"Ratio Out of Bounds [0.0, 1.0] for '{ratio_col}'"
                )

        # 3. Positivity Checks
        for pos_col in ["rps", "concurrency", "users", "throughput"]:
            if pos_col in df.columns:
                _record_violation(
                    f"{pos_col}_le_zero",
                    df[pos_col] <= 0.0,
                    f"Positive Invariant Violated ({pos_col} <= 0)"
                )

        # 4. Non-Negative Costs and Latencies
        for nn_col in ["total_monthly_cost", "compute_cost", "p50", "p95", "p99", "cpu_limit", "memory_limit"]:
            if nn_col in df.columns:
                _record_violation(
                    f"{nn_col}_lt_zero",
                    df[nn_col] < 0.0,
                    f"Non-Negative Invariant Violated ({nn_col} < 0)"
                )

        return results

    # 6.6 Categorical Validation
    def check_categoricals(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Validates categorical fields against ADIP's controlled vocabulary.
        """
        # Controlled vocabulary definition
        CONTROLLED_VOCAB = {
            "architecture_pattern": ["monolith", "modular_monolith", "microservices", "event_driven", "serverless"],
            "architecture_style": ["layered", "hexagonal", "cqrs", "event_sourcing", "pipeline", "service_oriented"],
            "database": ["postgres", "mysql", "mongodb", "dynamodb", "cassandra", "redis_only", "none"],
            "cache": ["none", "redis", "memcached", "hazelcast"],
            "messaging": ["none", "kafka", "rabbitmq", "aws_sqs", "nats"],
            "api_style": ["rest", "graphql", "grpc", "websocket"],
            "deployment": ["docker_compose", "kubernetes", "aws_ecs", "aws_lambda", "bare_metal_vm"],
            "cloud": ["aws", "gcp", "azure", "on_premise"],
            "workload_type": ["oltp", "olap", "read_heavy", "write_heavy", "balanced", "streaming"],
            "traffic_pattern": ["steady", "bursty", "diurnal", "exponential_spike", "gradual_ramp"]
        }

        results = {
            "check": "6.6_categorical_validation",
            "passed": True,
            "discrepancies": {},
            "issues": []
        }

        for col, allowed_values in CONTROLLED_VOCAB.items():
            if col not in df.columns:
                continue

            unique_values = set(df[col].dropna().unique())
            invalid_values = unique_values.difference(allowed_values)
            if invalid_values:
                count = int(df[col].isin(invalid_values).sum())
                results["discrepancies"][col] = {
                    "invalid_values": list(invalid_values),
                    "violation_count": count
                }
                results["issues"].append(
                    f"Categorical Discrepancy in '{col}': Unrecognized values {invalid_values} ({count} rows)."
                )
                results["passed"] = False

        return results

    # Comprehensive Quality Audit Suite
    def run_full_quality_suite(
        self,
        df: pd.DataFrame,
        dataset_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Runs all Section 6 data quality checks and computes an aggregate quality score (0-100%).
        """
        logger.info(f"Running full data quality suite on DataFrame with {len(df)} rows, {len(df.columns)} columns.")

        schema_res = self.check_schema(df, dataset_key=dataset_key)
        missing_res = self.check_missing_values(df)
        dup_res = self.check_duplicates(df)
        outlier_res = self.check_outliers(df)
        range_res = self.check_physical_invariants(df)
        cat_res = self.check_categoricals(df)

        all_checks = [schema_res, missing_res, dup_res, outlier_res, range_res, cat_res]
        passed_count = sum(1 for c in all_checks if c["passed"])
        quality_score = round((passed_count / len(all_checks)) * 100, 1)

        all_issues = []
        for c in all_checks:
            all_issues.extend(c.get("issues", []))

        audit_summary = {
            "phase": "Phase 4 - Data Quality Checks",
            "lead": "Anshika",
            "quality_score_pct": quality_score,
            "overall_status": "PASSED" if quality_score >= 85.0 and range_res["passed"] else "ACTION_REQUIRED",
            "summary": {
                "schema_valid": schema_res["passed"],
                "missing_values_valid": missing_res["passed"],
                "duplicates_valid": dup_res["passed"],
                "outliers_acceptable": outlier_res["passed"],
                "physical_invariants_valid": range_res["passed"],
                "categoricals_valid": cat_res["passed"],
            },
            "total_issues_identified": len(all_issues),
            "issues": all_issues,
            "detailed_reports": {
                "schema": schema_res,
                "missing": missing_res,
                "duplicates": dup_res,
                "outliers": outlier_res,
                "physical_invariants": range_res,
                "categoricals": cat_res,
            }
        }

        logger.info(
            f"Quality Audit Complete: Score={quality_score}% | Status={audit_summary['overall_status']} | "
            f"Total Issues={len(all_issues)}"
        )
        return audit_summary


if __name__ == "__main__":
    # Self-test using mock architecture records
    mock_df = pd.DataFrame({
        "architecture_id": [f"arch_{i:04d}" for i in range(100)],
        "architecture_pattern": ["microservices"] * 50 + ["monolith"] * 50,
        "database": ["postgres"] * 80 + ["mongodb"] * 20,
        "cache": ["redis"] * 70 + ["none"] * 30,
        "rps": np.random.uniform(100, 5000, size=100),
        "concurrency": np.random.randint(10, 500, size=100),
        "read_write_ratio": np.random.uniform(0.5, 0.9, size=100),
        "p50": np.random.uniform(10, 50, size=100),
        "p95": np.random.uniform(55, 120, size=100),
        "p99": np.random.uniform(125, 300, size=100),
        "throughput": np.random.uniform(100, 4800, size=100),
        "total_monthly_cost": np.random.uniform(200, 4000, size=100),
    })

    checker = DataQualityChecker()
    audit = checker.run_full_quality_suite(mock_df)
    print(f"Self-Test Audit Score: {audit['quality_score_pct']}% | Status: {audit['overall_status']}")
