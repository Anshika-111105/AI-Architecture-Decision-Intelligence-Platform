import pytest
import pandas as pd
import numpy as np
from ml.src.optimization.dataset_versioning import DatasetVersionManager


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "architecture_id": ["arch_001", "arch_002", "arch_003"],
        "rps": [1000.0, 2500.0, 5000.0],
        "p95": [24.5, 45.2, 110.8],
    })


@pytest.fixture
def version_manager(tmp_path):
    registry_file = tmp_path / "dataset_registry.json"
    return DatasetVersionManager(registry_path=str(registry_file))


def test_compute_dataframe_hash_deterministic(version_manager, sample_df):
    hash1 = version_manager.compute_dataframe_hash(sample_df)
    hash2 = version_manager.compute_dataframe_hash(sample_df.copy())
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256


def test_register_and_get_dataset_version(version_manager, sample_df):
    record = version_manager.register_dataset_version(
        df=sample_df,
        version_tag="v1.0_clean",
        description="Clean benchmark dataset test",
        source_evidence_types=["Type_B_Controlled_Benchmark"]
    )

    assert record["version_tag"] == "v1.0_clean"
    assert record["row_count"] == 3

    fetched = version_manager.get_version("v1.0_clean")
    assert fetched is not None
    assert fetched["dataset_hash"] == record["dataset_hash"]


def test_verify_integrity(version_manager, sample_df):
    version_manager.register_dataset_version(
        df=sample_df,
        version_tag="v1.0_clean",
        description="Integrity test"
    )

    is_valid, msg = version_manager.verify_integrity(sample_df, "v1.0_clean")
    assert is_valid is True
    assert "Integrity verified" in msg

    # Tampered dataframe
    tampered_df = sample_df.copy()
    tampered_df.loc[0, "rps"] = 99999.0
    is_tampered_valid, tamper_msg = version_manager.verify_integrity(tampered_df, "v1.0_clean")
    assert is_tampered_valid is False
    assert "Hash mismatch" in tamper_msg
