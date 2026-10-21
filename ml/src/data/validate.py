import yaml
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple
import pandas as pd
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [Anshika-DataValidation] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("ADIP_DataValidate")


class DataValidator:
    """
    Validates data integrity, schema ranges, provenance metadata,
    and prevents data leakage before training.
    """

    def __init__(self, features_cfg_path: str = "ml/configs/features.yaml",data_cfg_path: str = "ml/configs/data.yaml"):
        self.features_cfg_path = Path(features_cfg_path)
        self.data_cfg_path = Path(data_cfg_path)
        self.features_cfg = self._load_yaml(self.features_cfg_path)
        self.data_cfg = self._load_yaml(self.data_cfg_path)

    @staticmethod
    def _load_yaml(path: Path) -> Dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"YAML config missing: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def validate_provenance_manifest(self, manifest_path: Path) -> Tuple[bool, List[str]]:
        """Verifies that mandatory provenance fields exist in the source manifest."""
        issues = []
        if not manifest_path.exists():
            return False, [f"Manifest file missing: {manifest_path}"]

        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        required_keys = self.data_cfg.get("provenance_schema", {}).get("mandatory_fields", [])
        for k in required_keys:
            if k not in data:
                issues.append(f"Missing mandatory provenance field: '{k}'")

        is_valid = len(issues) == 0
        return is_valid, issues

    def validate_bounds(self, df: pd.DataFrame, dataset_name: str) -> Tuple[bool, List[str]]:
        """Validates numerical ranges and categorical allowances defined in features.yaml."""
        issues = []
        ds_specs = self.features_cfg.get("datasets", {}).get(dataset_name, {}).get("fields", {})

        for col, spec in ds_specs.items():
            if col not in df.columns:
                continue

            # Numerical range validation
            if "range" in spec:
                min_val, max_val = spec["range"]
                out_of_bounds = df[(df[col] < min_val) | (df[col] > max_val)]
                if len(out_of_bounds) > 0:
                    issues.append(
                        f"Column '{col}' has {len(out_of_bounds)} values outside valid range [{min_val}, {max_val}]."
                    )

            # Categorical allowed set validation
            if spec.get("type") == "categorical" and "allowed" in spec:
                allowed = set(spec["allowed"])
                invalid_cats = set(df[col].dropna().unique()) - allowed
                if invalid_cats:
                    issues.append(
                        f"Column '{col}' contains unrecognized categories: {invalid_cats}. Allowed: {allowed}"
                    )

        # Sanity check: Non-negative latency
        for lat_col in ["p50", "p90", "p95", "p99"]:
            if lat_col in df.columns:
                negatives = df[df[lat_col] <= 0]
                if len(negatives) > 0:
                    issues.append(f"Physical anomaly: {len(negatives)} records have {lat_col} <= 0 ms.")

        # Sanity check: Percentage bounds (0 - 100%)
        for pct_col in ["cpu", "error_rate", "availability_sla"]:
            if pct_col in df.columns:
                invalid_pct = df[(df[pct_col] < 0.0) | (df[pct_col] > 100.0)]
                if len(invalid_pct) > 0:
                    issues.append(f"Percentage anomaly: {len(invalid_pct)} records in '{pct_col}' outside [0, 100].")

        return len(issues) == 0, issues

    def check_leakage(self, feature_df: pd.DataFrame, target_columns: List[str]) -> Tuple[bool, List[str]]:
        """Ensures target variables or future information are not leaking into training features."""
        leaks = [col for col in target_columns if col in feature_df.columns]
        if leaks:
            return False, [f"DATA LEAKAGE DETECTED: Target columns {leaks} are present in feature matrix!"]
        return True, []


if __name__ == "__main__":
    validator = DataValidator()
    # Self-test provenance verification across initialized raw directories
    raw_base = Path("ml/data/raw")
    manifests = list(raw_base.glob("*/provenance_manifest.json"))
    logger.info(f"Auditing {len(manifests)} source provenance manifests...")

    all_passed = True
    for mf in manifests:
        passed, errors = validator.validate_provenance_manifest(mf)
        status = "PASSED" if passed else "FAILED"
        if not passed:
            all_passed = False
            logger.warning(f"[{status}] {mf.parent.name}: {errors}")

    if all_passed:
        logger.info("All raw source provenance manifests passed validation audit successfully.")
