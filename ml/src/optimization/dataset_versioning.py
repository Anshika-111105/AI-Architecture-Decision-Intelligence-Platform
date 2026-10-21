import os
import json
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [Ananya-DatasetVersioning] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("ADIP_DatasetVersioning")


class DatasetVersionManager:
    """
    Manages cryptographic dataset snapshots, version tags, and MLflow logging.
    Guarantees every surrogate model training run links to an immutable dataset version.
    """

    def __init__(
        self,
        registry_path: str = "mlruns/dataset_registry.json",
        tracking_uri: str = "mlruns",
        experiment_name: str = "ADIP_Surrogate_Optimization"
    ):
        self.registry_path = Path(registry_path)
        self.tracking_uri = tracking_uri
        self.experiment_name = experiment_name
        self._init_registry()

    def _init_registry(self) -> None:
        """Ensures the mlruns directory and dataset registry exist."""
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.registry_path.exists():
            initial_data = {
                "registry_version": "1.0",
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "versions": {}
            }
            with open(self.registry_path, "w", encoding="utf-8") as f:
                json.dump(initial_data, f, indent=2)
            logger.info(f"Initialized dataset registry at {self.registry_path}")

    @staticmethod
    def compute_dataframe_hash(df: pd.DataFrame) -> str:
        """
        Computes a deterministic SHA-256 hash over the sorted DataFrame values.
        """
        # Sort columns to maintain deterministic column ordering
        sorted_cols = sorted(df.columns)
        hash_obj = hashlib.sha256()
        # Hash column names
        hash_obj.update(",".join(sorted_cols).encode("utf-8"))
        # Hash sampled or full values
        data_bytes = pd.util.hash_pandas_object(df[sorted_cols], index=False).values.tobytes()
        hash_obj.update(data_bytes)
        return hash_obj.hexdigest()

    def register_dataset_version(
        self,
        df: pd.DataFrame,
        version_tag: str,
        description: str,
        source_evidence_types: Optional[List[str]] = None,
        file_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Registers a new dataset snapshot in the local registry and attempts MLflow logging.
        """
        df_hash = self.compute_dataframe_hash(df)
        timestamp = datetime.now(timezone.utc).isoformat()

        record = {
            "version_tag": version_tag,
            "dataset_hash": df_hash,
            "row_count": int(len(df)),
            "column_count": int(len(df.columns)),
            "columns": list(df.columns),
            "description": description,
            "source_evidence_types": source_evidence_types or ["Type_B_Controlled_Benchmark"],
            "file_path": file_path or f"ml/data/unified/{version_tag}.parquet",
            "registered_by": "Ananya (ML Optimization Lead)",
            "registered_at": timestamp,
        }

        # Update JSON registry
        with open(self.registry_path, "r", encoding="utf-8") as f:
            registry = json.load(f)

        registry["versions"][version_tag] = record
        registry["last_updated"] = timestamp

        with open(self.registry_path, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2)

        logger.info(
            f"Successfully registered dataset version '{version_tag}' "
            f"(Hash: {df_hash[:12]}..., Rows: {len(df):,})"
        )

        # Log to MLflow if available
        self._log_to_mlflow(record)

        return record

    def _log_to_mlflow(self, record: Dict[str, Any]) -> None:
        """Attempts to log dataset version metadata and tags to MLflow."""
        try:
            import mlflow
            mlflow.set_tracking_uri(self.tracking_uri)
            mlflow.set_experiment(self.experiment_name)

            with mlflow.start_run(run_name=f"dataset_version_{record['version_tag']}"):
                mlflow.set_tags({
                    "dataset.version_tag": record["version_tag"],
                    "dataset.hash": record["dataset_hash"],
                    "dataset.registered_by": record["registered_by"],
                    "dataset.row_count": str(record["row_count"]),
                })
                mlflow.log_dict(record, "dataset_metadata.json")
            logger.info(f"Logged dataset version '{record['version_tag']}' to MLflow.")
        except ImportError:
            logger.warning("MLflow not installed in environment; recorded snapshot in local JSON registry.")
        except Exception as e:
            logger.warning(f"Could not log to MLflow ({e}); local registry preserved.")

    def get_version(self, version_tag: str) -> Optional[Dict[str, Any]]:
        """Retrieves metadata for a registered dataset version tag."""
        if not self.registry_path.exists():
            return None
        with open(self.registry_path, "r", encoding="utf-8") as f:
            registry = json.load(f)
        return registry.get("versions", {}).get(version_tag)

    def verify_integrity(self, df: pd.DataFrame, version_tag: str) -> Tuple[bool, str]:
        """
        Verifies that a given DataFrame matches the exact hash of the registered version.
        """
        meta = self.get_version(version_tag)
        if not meta:
            return False, f"Version tag '{version_tag}' not found in registry."

        current_hash = self.compute_dataframe_hash(df)
        expected_hash = meta["dataset_hash"]

        if current_hash == expected_hash:
            return True, f"Integrity verified for '{version_tag}' (Hash: {current_hash[:12]})."
        else:
            return False, (
                f"Hash mismatch for '{version_tag}'! Expected {expected_hash[:12]}..., "
                f"got {current_hash[:12]}... (Dataset has been modified)."
            )
