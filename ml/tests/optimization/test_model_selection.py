import pytest
import numpy as np
import pandas as pd
from ml.src.optimization.model_selection import ModelSelector


@pytest.fixture
def synthetic_benchmark_data():
    np.random.seed(42)
    n = 100
    arch_ids = [f"arch_{i % 12:03d}" for i in range(n)]
    rps = np.random.uniform(500, 5000, size=n)
    concurrency = np.random.randint(10, 200, size=n)
    
    # Strong predictive signal for throughput: proportional to RPS with slight degradation
    throughput = (0.95 * rps) - (0.1 * concurrency) + np.random.normal(0, 10, size=n)
    throughput = np.clip(throughput, a_min=100.0, a_max=None)

    return pd.DataFrame({
        "architecture_id": arch_ids,
        "architecture_pattern": np.random.choice(["microservices", "monolith"], size=n),
        "database": np.random.choice(["postgres", "mongodb"], size=n),
        "rps": rps,
        "concurrency": concurrency,
        "throughput": throughput,
    })


@pytest.fixture
def selector():
    return ModelSelector()


def test_evaluate_candidates_and_select_champion(selector, synthetic_benchmark_data):
    result = selector.evaluate_candidates(
        df=synthetic_benchmark_data,
        target_name="throughput_model",
        target_col="throughput",
        group_col="architecture_id",
        n_splits=3
    )

    assert "candidates_evaluated" in result
    assert result["champion_model"] in ["Ridge_Linear", "Random_Forest", "Gradient_Boosting", "XGBoost"]
    assert result["champion_metrics"]["r2_mean"] > 0.80
    assert "acceptance_gate" in result


def test_acceptance_gate_passed(selector):
    mock_metrics = {
        "r2_mean": 0.91,
        "mape_mean": 8.5,
        "mae_mean": 50.0,
        "rmse_mean": 80.0,
    }

    gate = selector.check_acceptance_thresholds("throughput_model", mock_metrics)
    assert gate["all_passed"] is True
    assert gate["verdict"] == "APPROVED_FOR_RELEASE"


def test_acceptance_gate_rejected_below_r2(selector):
    mock_metrics = {
        "r2_mean": 0.65,  # Threshold requires >= 0.88
        "mape_mean": 10.0,
        "mae_mean": 50.0,
        "rmse_mean": 80.0,
    }

    gate = selector.check_acceptance_thresholds("throughput_model", mock_metrics)
    assert gate["all_passed"] is False
    assert gate["verdict"] == "REJECTED_BELOW_THRESHOLD"
    assert gate["checks"]["r2_passed"] is False
