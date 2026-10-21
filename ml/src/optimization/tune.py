import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator
from sklearn.model_selection import GroupKFold
from sklearn.metrics import r2_score, root_mean_squared_error, mean_absolute_error, mean_absolute_percentage_error
from sklearn.preprocessing import OneHotEncoder, RobustScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.compose import TransformedTargetRegressor

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [Ananya-HyperparameterTuning] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("ADIP_Tune")


class HyperparameterTuner:
    """
    Hyperparameter tuning and cross-validation engine for ADIP surrogate models.
    Supports:
      - 5 Target Models: Latency (p95), Throughput, Resources (CPU), Cost, Reliability (Error Rate)
      - Leakage-safe GroupKFold cross-validation on `architecture_id`
      - GridSearch and Optuna (Tree-structured Parzen Estimator / Bayesian Optimization)
      - Dynamic algorithm dispatch: XGBoost Regressor with GradientBoosting/RandomForest fallbacks
      - MLflow experiment tracking and dataset version tagging
    """

    SUPPORTED_TARGETS = {
        "latency": {"target_col": "p95", "metric": "rmse", "transform": "log1p"},
        "throughput": {"target_col": "throughput", "metric": "rmse", "transform": "none"},
        "resources": {"target_col": "cpu_utilization_ratio", "metric": "mae", "transform": "none"},
        "cost": {"target_col": "total_monthly_cost", "metric": "mae", "transform": "log1p"},
        "reliability": {"target_col": "error_rate", "metric": "mae", "transform": "none"},
    }

    def __init__(
        self,
        config_path: str = "ml/configs/training.yaml",
        random_state: int = 42
    ):
        self.config_path = Path(config_path)
        self.random_state = random_state
        self.config = self._load_config()
        logger.info("Initialized HyperparameterTuner.")

    def _load_config(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            return {}
        import yaml
        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _build_preprocessor(self, feature_df: pd.DataFrame) -> ColumnTransformer:
        """Constructs an isolated ColumnTransformer for numerical and categorical features."""
        cat_cols = feature_df.select_dtypes(include=["object", "category", "string"]).columns.tolist()
        num_cols = feature_df.select_dtypes(include=[np.number]).columns.tolist()

        transformers = []
        if num_cols:
            transformers.append(("num", RobustScaler(), num_cols))
        if cat_cols:
            transformers.append(("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat_cols))

        return ColumnTransformer(transformers=transformers, remainder="drop")

    def _get_base_regressor(self, model_family: str = "xgboost", **params):
        """Dispatches regressor with graceful fallback if XGBoost is not available."""
        if model_family.lower() == "xgboost":
            try:
                import xgboost as xgb
                return xgb.XGBRegressor(
                    random_state=self.random_state,
                    n_jobs=-1,
                    verbosity=0,
                    **params
                )
            except ImportError:
                logger.warning("XGBoost not installed; falling back to sklearn GradientBoostingRegressor.")
                from sklearn.ensemble import GradientBoostingRegressor
                gb_params = {k: v for k, v in params.items() if k in ["n_estimators", "max_depth", "learning_rate", "subsample"]}
                return GradientBoostingRegressor(random_state=self.random_state, **gb_params)
        elif model_family.lower() == "random_forest":
            from sklearn.ensemble import RandomForestRegressor
            rf_params = {k: v for k, v in params.items() if k in ["n_estimators", "max_depth", "min_samples_split", "min_samples_leaf"]}
            return RandomForestRegressor(random_state=self.random_state, n_jobs=-1, **rf_params)
        else:
            from sklearn.ensemble import GradientBoostingRegressor
            gb_params = {k: v for k, v in params.items() if k in ["n_estimators", "max_depth", "learning_rate", "subsample"]}
            return GradientBoostingRegressor(random_state=self.random_state, **gb_params)

    # =========================================================================
    # GroupKFold Cross-Validation Evaluation
    # =========================================================================
    def evaluate_pipeline_cv(
        self,
        pipeline: Pipeline,
        X: pd.DataFrame,
        y: pd.Series,
        groups: pd.Series,
        n_splits: int = 5
    ) -> Dict[str, float]:
        """
        Evaluates a model pipeline using GroupKFold across the specified architecture groups.
        Guarantees zero overlap of architecture variants between train and validation splits.
        """
        gkf = GroupKFold(n_splits=n_splits)
        r2_scores = []
        rmse_scores = []
        mae_scores = []
        mape_scores = []

        for train_idx, val_idx in gkf.split(X, y, groups=groups):
            X_tr, y_tr = X.iloc[train_idx], y.iloc[train_idx]
            X_va, y_va = X.iloc[val_idx], y.iloc[val_idx]

            pipeline.fit(X_tr, y_tr)
            preds = pipeline.predict(X_va)

            # Prevent negative predictions for strictly non-negative targets
            preds = np.clip(preds, a_min=0.0, a_max=None)

            r2 = float(r2_score(y_va, preds))
            rmse = float(root_mean_squared_error(y_va, preds))
            mae = float(mean_absolute_error(y_va, preds))
            # Safe MAPE avoiding division by zero
            nonzero_mask = y_va > 1e-6
            if nonzero_mask.sum() > 0:
                mape = float(mean_absolute_percentage_error(y_va[nonzero_mask], preds[nonzero_mask]) * 100.0)
            else:
                mape = 0.0

            r2_scores.append(r2)
            rmse_scores.append(rmse)
            mae_scores.append(mae)
            mape_scores.append(mape)

        return {
            "mean_r2": float(np.mean(r2_scores)),
            "std_r2": float(np.std(r2_scores)),
            "mean_rmse": float(np.mean(rmse_scores)),
            "mean_mae": float(np.mean(mae_scores)),
            "mean_mape": float(np.mean(mape_scores)),
        }

    # =========================================================================
    # GridSearch Optimization
    # =========================================================================
    def tune_with_grid_search(
        self,
        df: pd.DataFrame,
        target_name: str,
        param_grid: Optional[Dict[str, List[Any]]] = None,
        feature_cols: Optional[List[str]] = None,
        group_col: str = "architecture_id",
        dataset_version_tag: str = "v1.0_clean",
        n_splits: int = 5
    ) -> Dict[str, Any]:
        """
        Performs discrete grid search with GroupKFold validation over parameter combinations.
        """
        target_meta = self.SUPPORTED_TARGETS.get(target_name, {"target_col": target_name, "transform": "none"})
        target_col = target_meta["target_col"]
        if target_col not in df.columns:
            raise KeyError(f"Target column '{target_col}' not found in dataframe.")

        if group_col not in df.columns:
            raise KeyError(f"Group column '{group_col}' missing from dataframe.")

        # Filter features
        if feature_cols is None:
            excluded = [target_col, group_col, "experiment_id", "project_id", "workload_id", "timestamp"]
            feature_cols = [c for c in df.columns if c not in excluded]

        X = df[feature_cols].copy()
        y = df[target_col].copy()
        groups = df[group_col].copy()

        # Default grid if not specified
        if param_grid is None:
            param_grid = {
                "n_estimators": [50, 100, 200],
                "max_depth": [3, 5, 7],
                "learning_rate": [0.03, 0.08, 0.15],
            }

        # Build grid permutations
        import itertools
        keys = list(param_grid.keys())
        combos = [dict(zip(keys, v)) for v in itertools.product(*param_grid.values())]

        logger.info(
            f"Running GridSearch for target '{target_name}' ({target_col}) "
            f"over {len(combos)} combinations across {n_splits}-fold GroupKFold..."
        )

        preprocessor = self._build_preprocessor(X)
        best_score = -float("inf")
        best_params: Optional[Dict[str, Any]] = None
        best_metrics: Optional[Dict[str, float]] = None

        for params in combos:
            base_reg = self._get_base_regressor(model_family="xgboost", **params)
            if target_meta.get("transform") == "log1p":
                reg = TransformedTargetRegressor(regressor=base_reg, func=np.log1p, inverse_func=np.expm1)
            else:
                reg = base_reg

            pipe = Pipeline(steps=[("prep", preprocessor), ("model", reg)])
            metrics = self.evaluate_pipeline_cv(pipe, X, y, groups, n_splits=n_splits)

            # Maximize R² (or minimize RMSE)
            if metrics["mean_r2"] > best_score:
                best_score = metrics["mean_r2"]
                best_params = params
                best_metrics = metrics

        if best_params is None or best_metrics is None:
            raise RuntimeError(
                f"GridSearch failed to evaluate any parameter combinations for target '{target_name}'."
            )

        # Fit final estimator on entire dataset using best params
        final_base = self._get_base_regressor(model_family="xgboost", **best_params)
        if target_meta.get("transform") == "log1p":
            final_reg = TransformedTargetRegressor(regressor=final_base, func=np.log1p, inverse_func=np.expm1)
        else:
            final_reg = final_base
        final_pipeline = Pipeline(steps=[("prep", preprocessor), ("model", final_reg)])
        final_pipeline.fit(X, y)

        result = {
            "target_name": target_name,
            "target_col": target_col,
            "optimization_method": "GridSearch",
            "dataset_version_tag": dataset_version_tag,
            "best_params": best_params,
            "best_cv_metrics": best_metrics,
            "best_r2": round(best_metrics["mean_r2"], 4),
            "best_rmse": round(best_metrics["mean_rmse"], 4),
            "best_mae": round(best_metrics["mean_mae"], 4),
            "best_mape": round(best_metrics["mean_mape"], 4),
            "n_trials_evaluated": len(combos),
            "pipeline": final_pipeline,
        }

        # Log to MLflow if available
        self._log_tuning_to_mlflow(result)

        logger.info(
            f"GridSearch complete for '{target_name}'. Best R²: {result['best_r2']} "
            f"| RMSE: {result['best_rmse']} | Best Params: {best_params}"
        )
        return result

    # =========================================================================
    # Optuna Bayesian Optimization
    # =========================================================================
    def tune_with_optuna(
        self,
        df: pd.DataFrame,
        target_name: str,
        n_trials: int = 30,
        feature_cols: Optional[List[str]] = None,
        group_col: str = "architecture_id",
        dataset_version_tag: str = "v1.0_clean",
        n_splits: int = 5
    ) -> Dict[str, Any]:
        """
        Optimizes hyperparameters using Optuna's Tree-structured Parzen Estimator (TPE).
        Falls back to GridSearch if optuna is not installed.
        """
        try:
            import optuna
            optuna.logging.set_verbosity(optuna.logging.WARNING)
        except ImportError:
            logger.warning("Optuna not installed; falling back to GridSearch.")
            return self.tune_with_grid_search(
                df=df,
                target_name=target_name,
                feature_cols=feature_cols,
                group_col=group_col,
                dataset_version_tag=dataset_version_tag,
                n_splits=n_splits
            )

        target_meta = self.SUPPORTED_TARGETS.get(target_name, {"target_col": target_name, "transform": "none"})
        target_col = target_meta["target_col"]
        if target_col not in df.columns:
            raise KeyError(f"Target column '{target_col}' not found in dataframe.")

        if feature_cols is None:
            excluded = [target_col, group_col, "experiment_id", "project_id", "workload_id", "timestamp"]
            feature_cols = [c for c in df.columns if c not in excluded]

        X = df[feature_cols].copy()
        y = df[target_col].copy()
        groups = df[group_col].copy()
        preprocessor = self._build_preprocessor(X)

        logger.info(
            f"Starting Optuna TPE optimization ({n_trials} trials) for '{target_name}' "
            f"using {n_splits}-fold GroupKFold on '{group_col}'..."
        )

        def objective(trial):
            params = {
                "n_estimators": trial.suggest_int("n_estimators", 50, 300, step=25),
                "max_depth": trial.suggest_int("max_depth", 3, 9),
                "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.25, log=True),
                "subsample": trial.suggest_float("subsample", 0.7, 1.0),
                "colsample_bytree": trial.suggest_float("colsample_bytree", 0.7, 1.0),
                "min_child_weight": trial.suggest_int("min_child_weight", 1, 6),
            }

            base_reg = self._get_base_regressor(model_family="xgboost", **params)
            if target_meta.get("transform") == "log1p":
                reg = TransformedTargetRegressor(regressor=base_reg, func=np.log1p, inverse_func=np.expm1)
            else:
                reg = base_reg

            pipe = Pipeline(steps=[("prep", preprocessor), ("model", reg)])
            metrics = self.evaluate_pipeline_cv(pipe, X, y, groups, n_splits=n_splits)

            # Maximize R²
            return metrics["mean_r2"]

        study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=self.random_state))
        study.optimize(objective, n_trials=n_trials)

        best_params = study.best_params
        # Evaluate full metrics for best trial
        final_base = self._get_base_regressor(model_family="xgboost", **best_params)
        if target_meta.get("transform") == "log1p":
            final_reg = TransformedTargetRegressor(regressor=final_base, func=np.log1p, inverse_func=np.expm1)
        else:
            final_reg = final_base

        final_pipeline = Pipeline(steps=[("prep", preprocessor), ("model", final_reg)])
        best_metrics = self.evaluate_pipeline_cv(final_pipeline, X, y, groups, n_splits=n_splits)
        final_pipeline.fit(X, y)

        result = {
            "target_name": target_name,
            "target_col": target_col,
            "optimization_method": "Optuna_TPE",
            "dataset_version_tag": dataset_version_tag,
            "best_params": best_params,
            "best_cv_metrics": best_metrics,
            "best_r2": round(best_metrics["mean_r2"], 4),
            "best_rmse": round(best_metrics["mean_rmse"], 4),
            "best_mae": round(best_metrics["mean_mae"], 4),
            "best_mape": round(best_metrics["mean_mape"], 4),
            "n_trials_evaluated": len(study.trials),
            "pipeline": final_pipeline,
        }

        self._log_tuning_to_mlflow(result)
        logger.info(
            f"Optuna complete for '{target_name}'. Best R²: {result['best_r2']} "
            f"| RMSE: {result['best_rmse']} | Best Params: {best_params}"
        )
        return result

    # =========================================================================
    # MLflow Experiment Logging Helper
    # =========================================================================
    def _log_tuning_to_mlflow(self, result: Dict[str, Any]) -> None:
        """Logs hyperparameters and cross-validation metrics to MLflow."""
        try:
            import mlflow
            tracking_uri = self.config.get("mlflow", {}).get("tracking_uri", "mlruns")
            exp_name = self.config.get("mlflow", {}).get("experiment_name", "ADIP_Surrogate_Optimization")
            mlflow.set_tracking_uri(tracking_uri)
            mlflow.set_experiment(exp_name)

            run_name = f"tune_{result['target_name']}_{result['optimization_method']}_{result['dataset_version_tag']}"
            with mlflow.start_run(run_name=run_name):
                mlflow.set_tags({
                    "target_name": result["target_name"],
                    "dataset.version_tag": result["dataset_version_tag"],
                    "optimization_method": result["optimization_method"],
                    "engineer": "Ananya",
                })
                # Log best parameters
                for p_name, p_val in result["best_params"].items():
                    mlflow.log_param(p_name, p_val)

                # Log metrics
                mlflow.log_metric("cv_mean_r2", result["best_r2"])
                mlflow.log_metric("cv_mean_rmse", result["best_rmse"])
                mlflow.log_metric("cv_mean_mae", result["best_mae"])
                mlflow.log_metric("cv_mean_mape", result["best_mape"])

            logger.info(f"Logged tuning run '{run_name}' to MLflow.")
        except ImportError:
            logger.warning("MLflow not installed; skipping remote logging.")
        except Exception as e:
            logger.warning(f"Failed to log run to MLflow ({e}); continuing.")
