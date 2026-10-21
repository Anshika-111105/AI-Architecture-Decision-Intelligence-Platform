import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [Ananya-StatisticalValidation] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("ADIP_StatisticalValidator")


class StatisticalValidator:
    """
    Statistical validation engine for ADIP datasets.
    Analyzes:
      1. Feature and target distributions (mean, std, quantiles, skewness, kurtosis).
      2. Skewness categorization and transformation recommendations (e.g. log1p).
      3. Outlier profiling using robust IQR and Modified Z-scores (MAD).
      4. Feature-to-feature multicollinearity and target correlation hierarchies.
      5. Automated Markdown & JSON statistical health reporting.
    """

    def __init__(self, high_corr_threshold: float = 0.85, severe_skew_threshold: float = 1.0):
        self.high_corr_threshold = high_corr_threshold
        self.severe_skew_threshold = severe_skew_threshold
        logger.info(
            f"Initialized StatisticalValidator (corr_threshold={high_corr_threshold}, "
            f"skew_threshold={severe_skew_threshold})"
        )

    # =========================================================================
    # 1. Distribution & Skewness Analysis
    # =========================================================================
    def analyze_distributions(
        self,
        df: pd.DataFrame,
        columns: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Calculates parametric and non-parametric distribution statistics,
        skewness coefficient, kurtosis, and recommended scalers.
        """
        if columns is None:
            columns = df.select_dtypes(include=[np.number]).columns.tolist()

        distribution_summary = {}

        for col in columns:
            if col not in df.columns:
                continue

            series = df[col].dropna()
            if len(series) < 3:
                continue

            mean_val = float(series.mean())
            std_val = float(series.std(ddof=1)) if len(series) > 1 else 0.0
            median_val = float(series.median())
            q25 = float(series.quantile(0.25))
            q75 = float(series.quantile(0.75))
            iqr_val = q75 - q25
            min_val = float(series.min())
            max_val = float(series.max())

            # Skewness and Kurtosis
            skew_val = float(series.skew()) if std_val > 1e-9 else 0.0
            kurt_val = float(series.kurtosis()) if std_val > 1e-9 else 0.0

            # Skewness classification
            if abs(skew_val) < 0.5:
                skew_class = "approximately_symmetric"
                rec_transform = "standard_or_robust_scaler"
            elif 0.5 <= skew_val <= self.severe_skew_threshold:
                skew_class = "moderate_right_skew"
                rec_transform = "robust_scaler"
            elif -self.severe_skew_threshold <= skew_val <= -0.5:
                skew_class = "moderate_left_skew"
                rec_transform = "robust_scaler"
            elif skew_val > self.severe_skew_threshold:
                skew_class = "severe_right_skew"
                rec_transform = "log1p" if min_val >= 0 else "quantile_transformer"
            else:
                skew_class = "severe_left_skew"
                rec_transform = "quantile_transformer"

            distribution_summary[col] = {
                "count": int(len(series)),
                "mean": round(mean_val, 4),
                "std": round(std_val, 4),
                "median": round(median_val, 4),
                "iqr": round(iqr_val, 4),
                "q25": round(q25, 4),
                "q75": round(q75, 4),
                "min": round(min_val, 4),
                "max": round(max_val, 4),
                "skewness": round(skew_val, 4),
                "kurtosis": round(kurt_val, 4),
                "skew_classification": skew_class,
                "recommended_transformation": rec_transform,
            }

        return distribution_summary

    # =========================================================================
    # 2. Outlier Profiling (IQR & Modified Z-Score / MAD)
    # =========================================================================
    def profile_outliers(
        self,
        df: pd.DataFrame,
        columns: Optional[List[str]] = None,
        iqr_multiplier: float = 2.5
    ) -> Dict[str, Dict[str, Any]]:
        """
        Profiles outliers using non-parametric IQR fences and Modified Z-scores based on MAD.
        Separates benign saturation tails from unphysical deviations.
        """
        if columns is None:
            columns = df.select_dtypes(include=[np.number]).columns.tolist()

        outlier_summary = {}

        for col in columns:
            if col not in df.columns:
                continue

            series = df[col].dropna()
            n_total = len(series)
            if n_total < 4:
                continue

            q25 = series.quantile(0.25)
            q75 = series.quantile(0.75)
            iqr = q75 - q25

            lower_fence = q25 - (iqr_multiplier * iqr)
            upper_fence = q75 + (iqr_multiplier * iqr)

            iqr_outliers = series[(series < lower_fence) | (series > upper_fence)]
            iqr_outlier_count = int(len(iqr_outliers))
            iqr_outlier_pct = round((iqr_outlier_count / n_total) * 100.0, 2)

            # Modified Z-Score (Boris Iglewicz and David Hoaglin, 1993)
            # Mi = 0.6745 * (xi - median) / MAD
            median_val = series.median()
            abs_dev = (series - median_val).abs()
            mad_val = abs_dev.median()

            if mad_val > 1e-9:
                mod_z_scores = 0.6745 * abs_dev / mad_val
                mad_outlier_count = int((mod_z_scores > 3.5).sum())
            else:
                mad_outlier_count = 0

            mad_outlier_pct = round((mad_outlier_count / n_total) * 100.0, 2)

            outlier_summary[col] = {
                "n_observations": n_total,
                "iqr_lower_fence": round(float(lower_fence), 4),
                "iqr_upper_fence": round(float(upper_fence), 4),
                "iqr_outlier_count": iqr_outlier_count,
                "iqr_outlier_pct": iqr_outlier_pct,
                "mad_outlier_count": mad_outlier_count,
                "mad_outlier_pct": mad_outlier_pct,
                "has_extreme_outliers": (iqr_outlier_pct > 5.0 or mad_outlier_pct > 5.0),
            }

        return outlier_summary

    # =========================================================================
    # 3. Correlation Analysis & Multicollinearity
    # =========================================================================
    def analyze_correlations(
        self,
        df: pd.DataFrame,
        feature_cols: Optional[List[str]] = None,
        target_cols: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Computes Pearson (linear) and Spearman (rank monotonic) correlation matrices.
        Identifies collinear feature pairs and ranks predictive features per target.
        """
        numeric_df = df.select_dtypes(include=[np.number])
        if feature_cols is None:
            feature_cols = [c for c in numeric_df.columns if c not in (target_cols or [])]
        if target_cols is None:
            target_cols = [c for c in ["p95", "p99", "throughput", "cpu", "monthly_cost", "error_rate"] if c in numeric_df.columns]

        all_cols = list(set([c for c in feature_cols + target_cols if c in numeric_df.columns]))
        subset_df = numeric_df[all_cols].dropna()

        if len(subset_df) < 3 or len(all_cols) < 2:
            return {"high_multicollinearity_pairs": [], "target_correlations": {}}

        pearson_corr = subset_df.corr(method="pearson")
        spearman_corr = subset_df.corr(method="spearman")

        # Detect high multicollinearity among features
        high_corr_pairs = []
        valid_features = [f for f in feature_cols if f in subset_df.columns]
        for i in range(len(valid_features)):
            for j in range(i + 1, len(valid_features)):
                f1 = valid_features[i]
                f2 = valid_features[j]
                p_r = pearson_corr.loc[f1, f2]
                s_r = spearman_corr.loc[f1, f2]
                if abs(p_r) >= self.high_corr_threshold or abs(s_r) >= self.high_corr_threshold:
                    high_corr_pairs.append({
                        "feature_1": f1,
                        "feature_2": f2,
                        "pearson_r": round(float(p_r), 4),
                        "spearman_rho": round(float(s_r), 4),
                        "alert": "High collinearity detected — consider regularization or feature reduction.",
                    })

        # Rank predictive signals per target
        target_correlations = {}
        for target in target_cols:
            if target not in subset_df.columns:
                continue

            target_scores = []
            for f in valid_features:
                p_r = pearson_corr.loc[f, target]
                s_r = spearman_corr.loc[f, target]
                target_scores.append({
                    "feature": f,
                    "pearson_r": round(float(p_r), 4),
                    "spearman_rho": round(float(s_r), 4),
                    "abs_spearman": round(float(abs(s_r)), 4),
                })

            target_scores.sort(key=lambda x: x["abs_spearman"], reverse=True)
            target_correlations[target] = target_scores

        return {
            "high_multicollinearity_pairs": high_corr_pairs,
            "target_correlations": target_correlations,
        }

    # =========================================================================
    # 4. Comprehensive Validation Report
    # =========================================================================
    def generate_statistical_report(
        self,
        df: pd.DataFrame,
        dataset_version_tag: str = "v1.0_clean",
        output_report_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes full statistical validation pipeline and optionally writes a markdown report.
        """
        logger.info(f"Generating statistical health report for dataset '{dataset_version_tag}'...")

        distributions = self.analyze_distributions(df)
        outliers = self.profile_outliers(df)
        correlations = self.analyze_correlations(df)

        report = {
            "dataset_version_tag": dataset_version_tag,
            "row_count": len(df),
            "column_count": len(df.columns),
            "distributions": distributions,
            "outliers": outliers,
            "correlations": correlations,
            "status": "VALIDATED",
        }

        if output_report_path:
            out_p = Path(output_report_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            md_content = self._render_markdown_report(report)
            with open(out_p, "w", encoding="utf-8") as f:
                f.write(md_content)
            logger.info(f"Wrote statistical health markdown report to: {out_p}")

        return report

    def _render_markdown_report(self, report: Dict[str, Any]) -> str:
        """Renders statistical report into human-readable Markdown format."""
        tag = report["dataset_version_tag"]
        rows = report["row_count"]
        cols = report["column_count"]

        lines = [
            f"# ADIP — Statistical Validation Report (`{tag}`)",
            "",
            "> **Generated By:** Ananya (ML Optimization & Model Lifecycle Engineer)  ",
            "> **Purpose:** Statistical distribution, skewness, outlier, and collinearity audit.",
            "",
            "---",
            "",
            f"### Dataset Dimensions: {rows:,} Rows | {cols} Columns",
            "",
            "## 1. Distribution & Skewness Analysis",
            "",
            "| Column | Mean | Median | Std | Skewness | Kurtosis | Skew Class | Recommended Scaler |",
            "| :--- | :---: | :---: | :---: | :---: | :---: | :--- | :--- |",
        ]

        for col, stat in report["distributions"].items():
            lines.append(
                f"| `{col}` | {stat['mean']} | {stat['median']} | {stat['std']} | "
                f"{stat['skewness']} | {stat['kurtosis']} | `{stat['skew_classification']}` | `{stat['recommended_transformation']}` |"
            )

        lines.extend([
            "",
            "## 2. Outlier Profiling (Non-Parametric IQR & MAD)",
            "",
            "| Column | IQR Bounds | IQR Outliers | IQR Outlier % | MAD Outliers (Mod-Z > 3.5) | Extreme Outliers? |",
            "| :--- | :---: | :---: | :---: | :---: | :---: |",
        ])

        for col, stat in report["outliers"].items():
            bounds = f"[{stat['iqr_lower_fence']}, {stat['iqr_upper_fence']}]"
            lines.append(
                f"| `{col}` | {bounds} | {stat['iqr_outlier_count']} | {stat['iqr_outlier_pct']}% | "
                f"{stat['mad_outlier_count']} ({stat['mad_outlier_pct']}%) | **{stat['has_extreme_outliers']}** |"
            )

        lines.extend([
            "",
            "## 3. High Multicollinearity Warnings (|r| >= 0.85)",
            "",
        ])

        high_pairs = report["correlations"]["high_multicollinearity_pairs"]
        if not high_pairs:
            lines.append("✓ **No severe multicollinearity detected among numerical features.**")
        else:
            lines.extend([
                "| Feature 1 | Feature 2 | Pearson r | Spearman rho | Warning |",
                "| :--- | :--- | :---: | :---: | :--- |",
            ])
            for pair in high_pairs:
                lines.append(
                    f"| `{pair['feature_1']}` | `{pair['feature_2']}` | {pair['pearson_r']} | {pair['spearman_rho']} | {pair['alert']} |"
                )

        lines.append("")
        return "\n".join(lines)
