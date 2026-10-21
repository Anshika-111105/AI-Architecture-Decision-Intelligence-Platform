import pytest
import numpy as np
import pandas as pd
from ml.src.data.quality_checker import DataQualityChecker


@pytest.fixture
def sample_valid_df():
    """Generates a physically consistent, valid sample dataset for quality testing."""
    np.random.seed(42)
    n = 100
    p50 = np.random.uniform(10, 40, size=n)
    p90 = p50 + np.random.uniform(5, 20, size=n)
    p95 = p90 + np.random.uniform(5, 25, size=n)
    p99 = p95 + np.random.uniform(10, 50, size=n)
    
    return pd.DataFrame({
        "architecture_id": [f"arch_{i:04d}" for i in range(n)],
        "architecture_pattern": np.random.choice(["microservices", "monolith", "event_driven"], size=n),
        "database": np.random.choice(["postgres", "mongodb", "cassandra"], size=n),
        "cache": np.random.choice(["redis", "none", "memcached"], size=n),
        "messaging": np.random.choice(["kafka", "rabbitmq", "none"], size=n),
        "deployment": np.random.choice(["kubernetes", "aws_ecs", "docker_compose"], size=n),
        "cloud": np.random.choice(["aws", "gcp", "azure"], size=n),
        "rps": np.random.uniform(100, 5000, size=n),
        "concurrency": np.random.randint(10, 500, size=n),
        "read_write_ratio": np.random.uniform(0.1, 0.9, size=n),
        "p50": p50,
        "p90": p90,
        "p95": p95,
        "p99": p99,
        "throughput": np.random.uniform(90, 4900, size=n),
        "total_monthly_cost": np.random.uniform(150, 4500, size=n),
    })


@pytest.fixture
def checker():
    return DataQualityChecker()


# 6.1 Schema Validation Tests
def test_schema_valid(checker, sample_valid_df):
    result = checker.check_schema(sample_valid_df, required_keys=["architecture_id"])
    assert result["passed"] is True
    assert len(result["missing_required_columns"]) == 0
    assert len(result["null_primary_keys"]) == 0


def test_schema_missing_primary_key(checker, sample_valid_df):
    df_missing_pk = sample_valid_df.drop(columns=["architecture_id"])
    result = checker.check_schema(df_missing_pk, required_keys=["architecture_id"])
    assert result["passed"] is False
    assert "architecture_id" in result["missing_required_columns"]


def test_schema_null_primary_keys(checker, sample_valid_df):
    df_null_pk = sample_valid_df.copy()
    df_null_pk.loc[0:2, "architecture_id"] = None
    result = checker.check_schema(df_null_pk, required_keys=["architecture_id"])
    assert result["passed"] is False
    assert result["null_primary_keys"]["architecture_id"] == 3


# 6.2 Missing-Value Tests
def test_missing_values_expected_optional(checker, sample_valid_df):
    df_opt = sample_valid_df.copy()
    df_opt.loc[0:5, "cache"] = np.nan  # optional component
    result = checker.check_missing_values(df_opt, expected_optional_cols=["cache", "messaging"])
    assert result["passed"] is True
    assert "cache" in result["recommended_imputations"]
    assert result["recommended_imputations"]["cache"] == "constant_none"


def test_missing_values_unexpected_required(checker, sample_valid_df):
    df_unexp = sample_valid_df.copy()
    df_unexp.loc[0:5, "rps"] = np.nan  # mandatory field
    result = checker.check_missing_values(df_unexp, expected_optional_cols=["cache", "messaging"])
    assert result["passed"] is False
    assert "rps" in result["unexpected_missing_columns"]


# 6.3 Duplicate Detection Tests
def test_exact_duplicates_detected(checker, sample_valid_df):
    df_dup = pd.concat([sample_valid_df, sample_valid_df.iloc[[0]]], ignore_index=True)
    result = checker.check_duplicates(df_dup, id_col="architecture_id")
    assert result["passed"] is False
    assert result["exact_duplicates_count"] == 1


def test_primary_key_collision_detected(checker, sample_valid_df):
    df_dup_id = sample_valid_df.copy()
    df_dup_id.loc[1, "architecture_id"] = df_dup_id.loc[0, "architecture_id"]
    result = checker.check_duplicates(df_dup_id, id_col="architecture_id")
    assert result["passed"] is False
    assert result["id_collisions_count"] == 1


# 6.4 Outlier Analysis Tests
def test_outlier_detection_iqr(checker, sample_valid_df):
    df_outliers = sample_valid_df.copy()
    # Inject extreme tail latency spike
    df_outliers.loc[0, "p99"] = 50000.0
    result = checker.check_outliers(df_outliers, target_columns=["p99"], iqr_multiplier=2.5)
    assert result["outliers_by_column"]["p99"]["outlier_count"] >= 1
    assert result["outliers_by_column"]["p99"]["max"] == 50000.0


# 6.5 Physical Boundary Invariant Tests
def test_physical_invariants_valid(checker, sample_valid_df):
    result = checker.check_physical_invariants(sample_valid_df)
    assert result["passed"] is True
    assert len(result["violations"]) == 0


def test_percentile_monotonicity_violation(checker, sample_valid_df):
    df_invalid = sample_valid_df.copy()
    # p50 > p95 (impossible in reality)
    df_invalid.loc[0, "p50"] = 500.0
    df_invalid.loc[0, "p95"] = 100.0
    result = checker.check_physical_invariants(df_invalid)
    assert result["passed"] is False
    assert "p50_gt_p95" in result["violations"]


def test_ratio_bounds_violation(checker, sample_valid_df):
    df_invalid = sample_valid_df.copy()
    # read_write_ratio > 1.0 (impossible)
    df_invalid.loc[0, "read_write_ratio"] = 1.85
    result = checker.check_physical_invariants(df_invalid)
    assert result["passed"] is False
    assert "read_write_ratio_out_of_bounds" in result["violations"]


def test_negative_cost_violation(checker, sample_valid_df):
    df_invalid = sample_valid_df.copy()
    # Negative monthly cost
    df_invalid.loc[0, "total_monthly_cost"] = -120.0
    result = checker.check_physical_invariants(df_invalid)
    assert result["passed"] is False
    assert "total_monthly_cost_lt_zero" in result["violations"]


def test_negative_rps_violation(checker, sample_valid_df):
    df_invalid = sample_valid_df.copy()
    df_invalid.loc[0, "rps"] = -50.0
    result = checker.check_physical_invariants(df_invalid)
    assert result["passed"] is False
    assert "rps_le_zero" in result["violations"]


# 6.6 Categorical Controlled Vocabulary Tests
def test_categoricals_valid(checker, sample_valid_df):
    result = checker.check_categoricals(sample_valid_df)
    assert result["passed"] is True
    assert len(result["discrepancies"]) == 0


def test_categoricals_invalid_spelling(checker, sample_valid_df):
    df_invalid = sample_valid_df.copy()
    df_invalid.loc[0, "architecture_pattern"] = "micro-services-typo"
    result = checker.check_categoricals(df_invalid)
    assert result["passed"] is False
    assert "architecture_pattern" in result["discrepancies"]
    assert "micro-services-typo" in result["discrepancies"]["architecture_pattern"]["invalid_values"]


# Full Quality Suite Test
def test_full_quality_suite(checker, sample_valid_df):
    audit = checker.run_full_quality_suite(sample_valid_df)
    assert audit["quality_score_pct"] == 100.0
    assert audit["overall_status"] == "PASSED"
    assert audit["total_issues_identified"] == 0
