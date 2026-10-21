import pytest
import numpy as np
import pandas as pd
from ml.src.validation.statistical_validator import StatisticalValidator


@pytest.fixture
def sample_dataset():
    """Generates a dataset with known skewness, outliers, and collinearity."""
    np.random.seed(42)
    n = 150

    # Normal distribution (symmetric)
    symmetric_feat = np.random.normal(loc=100.0, scale=15.0, size=n)

    # Exponential distribution (heavy right skew, typical for latency p99)
    right_skew_target = np.random.exponential(scale=50.0, size=n) + 10.0

    # Strong collinear pair (r > 0.90)
    collinear_base = np.random.uniform(10, 500, size=n)
    collinear_feat = collinear_base * 1.5 + np.random.normal(0, 5, size=n)

    df = pd.DataFrame({
        "architecture_id": [f"arch_{i % 20:03d}" for i in range(n)],
        "symmetric_feat": symmetric_feat,
        "collinear_base": collinear_base,
        "collinear_feat": collinear_feat,
        "p95": right_skew_target,
        "throughput": np.random.uniform(500, 5000, size=n),
    })

    # Inject an outlier in symmetric_feat
    df.loc[0, "symmetric_feat"] = 800.0
    return df


@pytest.fixture
def validator():
    return StatisticalValidator(high_corr_threshold=0.85, severe_skew_threshold=1.0)


def test_distribution_analysis_skew_classification(validator, sample_dataset):
    summary = validator.analyze_distributions(sample_dataset, columns=["symmetric_feat", "p95"])
    assert "symmetric_feat" in summary
    assert "p95" in summary

    # p95 was generated with exponential distribution -> severe right skew
    assert summary["p95"]["skewness"] > 0.8
    assert summary["p95"]["recommended_transformation"] in ["log1p", "robust_scaler", "quantile_transformer"]
    assert summary["p95"]["q75"] >= summary["p95"]["q25"]


def test_outlier_profiling_iqr_and_mad(validator, sample_dataset):
    outliers = validator.profile_outliers(sample_dataset, columns=["symmetric_feat"])
    feat_stats = outliers["symmetric_feat"]

    # Since row 0 was set to 800.0, it should be detected as an outlier
    assert feat_stats["iqr_outlier_count"] >= 1
    assert feat_stats["has_extreme_outliers"] is True or feat_stats["iqr_outlier_pct"] > 0.0


def test_correlations_and_collinearity(validator, sample_dataset):
    res = validator.analyze_correlations(
        sample_dataset,
        feature_cols=["symmetric_feat", "collinear_base", "collinear_feat"],
        target_cols=["p95", "throughput"]
    )

    high_pairs = res["high_multicollinearity_pairs"]
    assert len(high_pairs) >= 1
    pair_names = [(p["feature_1"], p["feature_2"]) for p in high_pairs]
    assert ("collinear_base", "collinear_feat") in pair_names or ("collinear_feat", "collinear_base") in pair_names

    # Check target correlations ranking
    assert "p95" in res["target_correlations"]
    assert len(res["target_correlations"]["p95"]) == 3


def test_generate_statistical_report(validator, sample_dataset, tmp_path):
    report_file = tmp_path / "test_report.md"
    report = validator.generate_statistical_report(
        df=sample_dataset,
        dataset_version_tag="v1.0_test",
        output_report_path=str(report_file)
    )

    assert report["dataset_version_tag"] == "v1.0_test"
    assert report["status"] == "VALIDATED"
    assert report_file.exists()
    content = report_file.read_text(encoding="utf-8")
    assert "Statistical Validation Report" in content
