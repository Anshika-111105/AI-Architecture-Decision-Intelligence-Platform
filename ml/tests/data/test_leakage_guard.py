import pytest
import pandas as pd
import numpy as np
from ml.src.data.leakage_guard import LeakageGuard
from ml.src.data.split import ArchitectureDataSplitter


@pytest.fixture
def guard():
    return LeakageGuard()


@pytest.fixture
def clean_candidate_features():
    return [
        "domain", "users", "rps", "concurrency", "read_write_ratio",
        "architecture_pattern", "database", "cache", "messaging",
        "service_count", "replica_count", "graph_depth", "max_fan_out",
        "architecture_complexity_score", "rps_per_service"
    ]


@pytest.fixture
def sample_split_dfs():
    """Generates disjoint Train/Val/Test partitions using GroupShuffleSplit."""
    np.random.seed(42)
    n = 120
    df = pd.DataFrame({
        "architecture_id": [f"arch_{i % 30:03d}" for i in range(n)],
        "architecture_pattern": ["microservices"] * n,
        "database": ["postgres"] * n,
        "cache": ["redis"] * n,
        "messaging": ["kafka"] * n,
        "deployment": ["kubernetes"] * n,
        "cloud": ["aws"] * n,
        "rps": np.random.uniform(100, 3000, size=n),
        "concurrency": np.random.randint(10, 300, size=n),
        "p99": np.random.uniform(50, 400, size=n),
        "total_monthly_cost": np.random.uniform(300, 2500, size=n)
    })

    splitter = ArchitectureDataSplitter(train_ratio=0.70, val_ratio=0.15, test_ratio=0.15, random_state=42)
    train_df, val_df, test_df = splitter.group_split_by_architecture(df, group_col="architecture_id")
    return train_df, val_df, test_df


# 7.2 3-Tier Feature Classification Tests
def test_feature_tier_classification(guard):
    assert guard.classify_feature("rps") == "USER_SUPPLIED"
    assert guard.classify_feature("budget") == "USER_SUPPLIED"
    assert guard.classify_feature("graph_depth") == "DERIVED_STRUCTURAL"
    assert guard.classify_feature("architecture_complexity_score") == "DERIVED_STRUCTURAL"
    assert guard.classify_feature("p99") == "OBSERVED_OUTCOMES"
    assert guard.classify_feature("total_monthly_cost") == "OBSERVED_OUTCOMES"
    assert guard.classify_feature("cpu_utilization_ratio") == "OBSERVED_OUTCOMES"


def test_feature_matrix_clean(guard, clean_candidate_features):
    result = guard.audit_feature_matrix_tier_compliance(clean_candidate_features)
    assert result["passed"] is True
    assert result["leaked_observed_outcomes_count"] == 0
    assert len(result["issues"]) == 0


def test_feature_matrix_leaked_outcomes(guard, clean_candidate_features):
    corrupted_features = clean_candidate_features + ["p50", "cpu_utilization_ratio", "throughput"]
    result = guard.audit_feature_matrix_tier_compliance(corrupted_features)
    assert result["passed"] is False
    assert result["leaked_observed_outcomes_count"] == 3
    assert "p50" in result["leaked_observed_outcomes"]
    assert "cpu_utilization_ratio" in result["leaked_observed_outcomes"]


# 7.1 Target Leakage Tests
def test_target_leakage_clean(guard, clean_candidate_features):
    result = guard.audit_target_leakage(clean_candidate_features, target_name="p99")
    assert result["passed"] is True
    assert result["detected_leaks_count"] == 0


def test_target_leakage_detected_latency(guard, clean_candidate_features):
    # p50 or observed cache_hit_rate leaking into p99 latency model
    leaky_features = clean_candidate_features + ["p50", "observed_cache_hit_rate"]
    result = guard.audit_target_leakage(leaky_features, target_name="p99")
    assert result["passed"] is False
    assert result["detected_leaks_count"] == 2
    assert "p50" in result["detected_leaks"]
    assert "observed_cache_hit_rate" in result["detected_leaks"]


def test_target_leakage_detected_cost(guard, clean_candidate_features):
    # compute_cost component leaking into total_monthly_cost model
    leaky_features = clean_candidate_features + ["compute_cost", "database_cost"]
    result = guard.audit_target_leakage(leaky_features, target_name="total_monthly_cost")
    assert result["passed"] is False
    assert result["detected_leaks_count"] == 2
    assert "compute_cost" in result["detected_leaks"]


# 7.4 Train/Test Contamination & Group-Based Splitting Tests
def test_train_test_group_isolation_clean(guard, sample_split_dfs):
    train_df, val_df, test_df = sample_split_dfs
    result = guard.audit_train_test_contamination(
        train_df=train_df,
        test_df=test_df,
        val_df=val_df,
        group_col="architecture_id"
    )
    assert result["passed"] is True
    assert result["overlap_train_test_count"] == 0
    assert result["overlap_train_val_count"] == 0
    assert len(result["issues"]) == 0


def test_train_test_contamination_detected(guard, sample_split_dfs):
    train_df, val_df, test_df = sample_split_dfs
    # Inject deliberate contamination: copy an architecture from train into test
    contaminated_test = pd.concat([test_df, train_df.iloc[[0]]], ignore_index=True)
    result = guard.audit_train_test_contamination(
        train_df=train_df,
        test_df=contaminated_test,
        val_df=val_df,
        group_col="architecture_id"
    )
    assert result["passed"] is False
    assert result["overlap_train_test_count"] >= 1


# 7.3 Temporal Leakage Tests
def test_temporal_leakage_valid(guard):
    train_df = pd.DataFrame({"collection_timestamp": pd.date_range("2026-01-01", periods=50, freq="D")})
    test_df = pd.DataFrame({"collection_timestamp": pd.date_range("2026-02-25", periods=20, freq="D")})
    result = guard.audit_temporal_leakage(train_df, test_df, timestamp_col="collection_timestamp")
    assert result["passed"] is True
    assert result["is_strictly_chronological"] is True


def test_temporal_leakage_detected(guard):
    # Test split has timestamps earlier than train split (learning from future)
    train_df = pd.DataFrame({"collection_timestamp": pd.date_range("2026-02-01", periods=30, freq="D")})
    test_df = pd.DataFrame({"collection_timestamp": pd.date_range("2026-01-15", periods=20, freq="D")})
    result = guard.audit_temporal_leakage(train_df, test_df, timestamp_col="collection_timestamp")
    assert result["passed"] is False
    assert result["is_strictly_chronological"] is False
    assert len(result["issues"]) >= 1


# Full Leakage Suite Test
def test_full_leakage_audit_approved(guard, clean_candidate_features, sample_split_dfs):
    train_df, val_df, test_df = sample_split_dfs
    audit = guard.run_full_leakage_audit(
        candidate_features=clean_candidate_features,
        target_name="p99",
        train_df=train_df,
        test_df=test_df,
        val_df=val_df,
        group_col="architecture_id",
        timestamp_col=None
    )
    assert audit["is_leakage_free"] is True
    assert audit["overall_status"] == "APPROVED_LEAKAGE_FREE"
    assert audit["total_issues_identified"] == 0
