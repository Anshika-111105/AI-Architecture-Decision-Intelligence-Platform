import pytest
import numpy as np
import pandas as pd
from ml.src.optimization.tune import HyperparameterTuner


@pytest.fixture
def synthetic_perf_data():
    """Generates synthetic dataset linking architecture + workload to latency."""
    np.random.seed(42)
    n = 120
    arch_ids = [f"arch_{i % 15:03d}" for i in range(n)]
    rps = np.random.uniform(500, 10000, size=n)
    concurrency = np.random.randint(10, 500, size=n)
    service_count = np.random.randint(1, 10, size=n)
    
    # Ground truth relationship: Latency increases with RPS and concurrency, decreases with replicas/services
    p95 = 5.0 + (0.005 * rps) + (0.08 * concurrency) - (0.5 * service_count) + np.random.normal(0, 2, size=n)
    p95 = np.clip(p95, a_min=1.0, a_max=None)

    return pd.DataFrame({
        "architecture_id": arch_ids,
        "architecture_pattern": np.random.choice(["microservices", "monolith"], size=n),
        "database": np.random.choice(["postgres", "mongodb"], size=n),
        "rps": rps,
        "concurrency": concurrency,
        "service_count": service_count,
        "p95": p95,
        "total_monthly_cost": 50.0 + (10.0 * service_count) + np.random.normal(0, 5, size=n),
    })


@pytest.fixture
def tuner():
    return HyperparameterTuner()


def test_grid_search_latency_target(tuner, synthetic_perf_data):
    param_grid = {
        "n_estimators": [30, 60],
        "max_depth": [3, 5],
        "learning_rate": [0.08],
    }

    result = tuner.tune_with_grid_search(
        df=synthetic_perf_data,
        target_name="latency",
        param_grid=param_grid,
        dataset_version_tag="v1.0_clean",
        n_splits=3
    )

    assert result["target_name"] == "latency"
    assert result["optimization_method"] == "GridSearch"
    assert result["best_r2"] > 0.50
    assert "n_estimators" in result["best_params"]
    assert result["pipeline"] is not None


def test_tuner_cost_target_log1p(tuner, synthetic_perf_data):
    param_grid = {
        "n_estimators": [40],
        "max_depth": [3],
        "learning_rate": [0.1],
    }

    result = tuner.tune_with_grid_search(
        df=synthetic_perf_data,
        target_name="cost",
        param_grid=param_grid,
        dataset_version_tag="v1.0_clean",
        n_splits=3
    )

    assert result["target_name"] == "cost"
    assert result["best_r2"] > 0.60
    assert result["best_mae"] < 20.0


def test_grid_search_empty_param_grid(tuner, synthetic_perf_data):
    param_grid = {"n_estimators": []}
    with pytest.raises(RuntimeError, match="GridSearch failed to evaluate any parameter combinations"):
        tuner.tune_with_grid_search(
            df=synthetic_perf_data,
            target_name="latency",
            param_grid=param_grid,
            dataset_version_tag="v1.0_clean",
            n_splits=3
        )

