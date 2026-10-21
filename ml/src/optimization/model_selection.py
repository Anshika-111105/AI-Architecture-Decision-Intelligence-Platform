import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import numpy as np
import pandas as pd
import yaml
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.preprocessing import OneHotEncoder, RobustScaler
from sklearn.model_selection import GroupKFold
from sklearn.metrics import r2_score, root_mean_squared_error, mean_absolute_error, mean_absolute_percentage_error

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [Ananya-ModelSelection] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("ADIP_ModelSelection")


class ModelSelector:
    """
    Candidate model comparison and automated acceptance gating engine.
    Compares baseline, ensemble, and boosted trees against the strict thresholds
    defined in `ml/configs/evaluation.yaml`.
    """

    def __init__(
        self,
        eval_config_path: str = "ml/configs/evaluation.yaml",
        random_state: int = 42
    ):
        self.eval_config_path = Path(eval_config_path)
        self.random_state = random_state
        self.eval_config = self._load_eval_config()
        self.thresholds = self.eval_config.get("model_acceptance_thresholds", {})
        logger.info("Initialized ModelSelector with acceptance criteria.")

    def _load_eval_config(self) -> Dict[str, Any]:
        if not self.eval_config_path.exists():
            return {}
        with open(self.eval_config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _build_preprocessor(self, X: pd.DataFrame) -> ColumnTransformer:
        cat_cols = X.select_dtypes(include=["object", "category", "string"]).columns.tolist()
        num_cols = X.select_dtypes(include=[np.number]).columns.tolist()

        transformers = []
        if num_cols:
            transformers.append(("num", RobustScaler(), num_cols))
        if cat_cols:
            transformers.append(("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat_cols))

        return ColumnTransformer(transformers=transformers, remainder="drop")

    def _get_candidate_models(self) -> Dict[str, Any]:
        """Returns candidate model algorithms for benchmarking."""
        candidates = {
            "Ridge_Linear": Ridge(alpha=1.0, random_state=self.random_state),
            "Random_Forest": RandomForestRegressor(n_estimators=100, max_depth=8, random_state=self.random_state, n_jobs=-1),
            "Gradient_Boosting": GradientBoostingRegressor(n_estimators=100, max_depth=5, learning_rate=0.08, random_state=self.random_state),
        }

        try:
            import xgboost as xgb
            candidates["XGBoost"] = xgb.XGBRegressor(
                n_estimators=120,
                max_depth=6,
                learning_rate=0.08,
                random_state=self.random_state,
                n_jobs=-1,
                verbosity=0
            )
        except ImportError:
            pass

        return candidates

    def evaluate_candidates(
        self,
        df: pd.DataFrame,
        target_name: str,
        target_col: str,
        group_col: str = "architecture_id",
        feature_cols: Optional[List[str]] = None,
        n_splits: int = 5
    ) -> Dict[str, Any]:
        """
        Runs GroupKFold cross-validation across all candidate algorithms and evaluates
        metrics ($R^2$, RMSE, MAE, MAPE).
        """
        if target_col not in df.columns:
            raise KeyError(f"Target column '{target_col}' not found in DataFrame.")

        if feature_cols is None:
            excluded = [target_col, group_col, "experiment_id", "project_id", "workload_id", "timestamp"]
            feature_cols = [c for c in df.columns if c not in excluded]

        X = df[feature_cols].copy()
        y = df[target_col].copy()
        groups = df[group_col].copy()

        preprocessor = self._build_preprocessor(X)
        candidates = self._get_candidate_models()
        gkf = GroupKFold(n_splits=n_splits)

        results = {}

        for name, model in candidates.items():
            pipe = Pipeline(steps=[("prep", preprocessor), ("model", model)])

            r2_list, rmse_list, mae_list, mape_list = [], [], [], []

            for train_idx, val_idx in gkf.split(X, y, groups=groups):
                X_tr, y_tr = X.iloc[train_idx], y.iloc[train_idx]
                X_va, y_va = X.iloc[val_idx], y.iloc[val_idx]

                pipe.fit(X_tr, y_tr)
                preds = np.clip(pipe.predict(X_va), a_min=0.0, a_max=None)

                r2_list.append(float(r2_score(y_va, preds)))
                rmse_list.append(float(root_mean_squared_error(y_va, preds)))
                mae_list.append(float(mean_absolute_error(y_va, preds)))

                nonzero_mask = y_va > 1e-6
                if nonzero_mask.sum() > 0:
                    mape_list.append(float(mean_absolute_percentage_error(y_va[nonzero_mask], preds[nonzero_mask]) * 100.0))
                else:
                    mape_list.append(0.0)

            results[name] = {
                "r2_mean": round(float(np.mean(r2_list)), 4),
                "r2_std": round(float(np.std(r2_list)), 4),
                "rmse_mean": round(float(np.mean(rmse_list)), 4),
                "mae_mean": round(float(np.mean(mae_list)), 4),
                "mape_mean": round(float(np.mean(mape_list)), 4),
            }

        # Select best model based on R2
        champion_name = max(results.keys(), key=lambda k: results[k]["r2_mean"])

        # Check against acceptance thresholds
        gate_status = self.check_acceptance_thresholds(
            target_name=target_name,
            metrics=results[champion_name]
        )

        return {
            "target_name": target_name,
            "target_col": target_col,
            "candidates_evaluated": results,
            "champion_model": champion_name,
            "champion_metrics": results[champion_name],
            "acceptance_gate": gate_status,
        }

    def check_acceptance_thresholds(
        self,
        target_name: str,
        metrics: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Validates model performance metrics against evaluation.yaml thresholds.
        """
        spec = self.thresholds.get(target_name, {})
        thresh = spec.get("thresholds", {})

        r2_min = thresh.get("r2_min", 0.80)
        mape_max = thresh.get("mape_max_pct", 20.0)
        mae_max = thresh.get("mae_max", float("inf"))
        rmse_max = thresh.get("rmse_max", float("inf"))

        checks = {
            "r2_passed": bool(metrics["r2_mean"] >= r2_min),
            "mape_passed": bool(metrics["mape_mean"] <= mape_max),
            "mae_passed": bool(metrics["mae_mean"] <= mae_max),
            "rmse_passed": bool(metrics["rmse_mean"] <= rmse_max),
        }

        all_passed = all(checks.values())

        return {
            "target_model": target_name,
            "all_passed": all_passed,
            "verdict": "APPROVED_FOR_RELEASE" if all_passed else "REJECTED_BELOW_THRESHOLD",
            "thresholds_applied": {
                "r2_min": r2_min,
                "mape_max_pct": mape_max,
                "mae_max": mae_max,
                "rmse_max": rmse_max,
            },
            "checks": checks,
        }
