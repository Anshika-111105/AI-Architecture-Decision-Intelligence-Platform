# ADIP — ML Optimization & Model Lifecycle Engineering Guide

> **Author:** Ananya (ML Optimization & Model Lifecycle Engineer)  
> **Project:** AI-Powered Architecture Decision Intelligence Platform (ADIP)  
> **Status:** Operational & Validated  
> **Date:** October 2026  

---

## 1. Scope & Ownership

As **ML Optimization & Model Lifecycle Engineer**, my ownership spans:
- `ml/configs/training.yaml` — Training pipelines, preprocessing, hyperparameter search spaces, and MLflow configuration.
- `ml/configs/evaluation.yaml` — Quantitative acceptance gates ($R^2$, RMSE, MAE, MAPE) and physical invariant rules across all 5 surrogate targets.
- `ml/src/optimization/` — Hyperparameter tuning (`tune.py`), model selection (`model_selection.py`), and dataset version tracking (`dataset_versioning.py`).
- `ml/src/validation/statistical_validator.py` — Distribution profiling, skewness classification, outlier detection, and multicollinearity audits.
- `mlruns/` — MLflow experiment store and immutable dataset registry.
- `ml/tests/optimization/` — Comprehensive test coverage for optimization and lifecycle components.

---

## 2. Statistical Validation Methodology ([`statistical_validator.py`](file:///e:/AI-Architecture-Decision-Intelligence-Platform/ml/src/validation/statistical_validator.py))

Software performance and resource telemetry diverge sharply from classical Gaussian assumptions. To prepare raw telemetry for surrogate modeling, the statistical validator performs 4 analyses:

### 2.1 Distribution Profiling & Skewness Classification
Evaluates parametric ($\mu, \sigma$) and non-parametric ($\text{median}, \text{IQR}, q_{25}, q_{75}$) metrics.
Skewness is categorized using the Fisher-Pearson coefficient:
- **Approximately Symmetric ($|\text{skew}| < 0.5$):** Scaled via `RobustScaler` or `StandardScaler`.
- **Moderate Skew ($0.5 \le |\text{skew}| \le 1.0$):** Scaled via `RobustScaler`.
- **Severe Right Skew ($\text{skew} > 1.0$):** Typical for $p_{99}$ latency and heavy cloud bills. Automatically flagged for $\log(1 + x)$ target transformation (`TransformedTargetRegressor`) to compress exponential tails.

### 2.2 Dual Non-Parametric Outlier Profiling
- **Tukey's IQR Fences:** $[Q_1 - 2.5 \times \text{IQR}, \; Q_3 + 2.5 \times \text{IQR}]$
- **Modified Z-Score via Median Absolute Deviation (MAD):**
  $$M_i = \frac{0.6745 \cdot |x_i - \tilde{x}|}{\text{MAD}}$$
  Observations with $M_i > 3.5$ are profiled to distinguish genuine system saturation boundaries (e.g., latency spikes at 25,000 RPS) from corrupt measurements.

### 2.3 Multicollinearity & Predictive Signal Ranking
- Detects feature pairs with Pearson $|r| \ge 0.85$ or Spearman $|\rho| \ge 0.85$ (e.g. `rps` vs `concurrency` or `node_count` vs `edge_count`) to guard against tree split instability.
- Ranks top predictive signals for each target variable using monotonic rank correlation ($|\rho|$).

---

## 3. Dataset Versioning in MLflow ([`dataset_versioning.py`](file:///e:/AI-Architecture-Decision-Intelligence-Platform/ml/src/optimization/dataset_versioning.py))

To enforce reproducibility (Section 42 of ADIP specification), surrogate models are never trained on unversioned or moving data.
- **Cryptographic Hashing:** Computes deterministic SHA-256 signatures over sorted column names and DataFrame bytes.
- **Tagging Protocol:** Every training run pins tags:
  - `dataset.version_tag`: e.g. `v1.0_clean`, `v1.1_augmented`
  - `dataset.hash`: Full 64-character SHA-256 hash
  - `dataset.row_count`: Exact row count
- **Audit Verification:** `verify_integrity(df, version_tag)` validates whether local data matches the immutable registry before training starts.

---

## 4. Hyperparameter Tuning Architecture ([`tune.py`](file:///e:/AI-Architecture-Decision-Intelligence-Platform/ml/src/optimization/tune.py))

### 4.1 Strict Group Isolation
Cross-validation uses `GroupKFold(n_splits=5, groups=df["architecture_id"])`.
**Critical Invariant:** All variants and trials of a given architecture ID remain strictly on one side of the fold. If `arch_042` is in validation, no row with `arch_042` may appear in training.

### 4.2 Search Strategies
1. **GridSearchCV:** Systematic grid exploration over `n_estimators`, `max_depth`, `learning_rate`, `subsample`, and regularization weights.
2. **Optuna (TPE Sampler):** Bayesian tree-structured Parzen estimators optimizing continuous and log-uniform parameters over $N$ trials.

### 4.3 Multi-Target Support
Supports all 5 surrogate models:
1. `latency`: Target `p95` (with `log1p` target transform).
2. `throughput`: Target `throughput` (bounded non-negative).
3. `resources`: Target `cpu_utilization_ratio` (bounded $[0.0, 1.0]$).
4. `cost`: Target `total_monthly_cost` (with `log1p` transform).
5. `reliability`: Target `error_rate` (bounded $[0.0, 1.0]$).

---

## 5. Model Acceptance Gates ([`evaluation.yaml`](file:///e:/AI-Architecture-Decision-Intelligence-Platform/ml/configs/evaluation.yaml))

A trained model cannot be promoted to champion status without satisfying automated quality thresholds:

| Model | Primary Target | Min $R^2$ | Max MAPE | Max MAE | Physical Invariants |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Latency** | $p_{95}$ (ms) | $\ge 0.85$ | $\le 18.0\%$ | $\le 25\text{ ms}$ | $\hat{p}_{50} \le \hat{p}_{95} \le \hat{p}_{99}$ |
| **Throughput** | Requests / sec | $\ge 0.88$ | $\le 12.0\%$ | $\le 150\text{ RPS}$ | $\hat{\text{throughput}} \ge 0$ |
| **Resource** | CPU Ratio $[0, 1]$ | $\ge 0.80$ | $\le 15.0\%$ | $\le 0.08$ | $\hat{\text{cpu}} \in [0.0, 1.0]$ |
| **Cost** | USD / month | $\ge 0.90$ | $\le 15.0\%$ | $\le \$75.00$ | $\hat{\text{cost}} > 0$ |
| **Reliability** | Error Rate $[0, 1]$ | $\ge 0.80$ | $\le 20.0\%$ | $\le 0.02$ | $\hat{\text{err}} \in [0.0, 1.0]$ |

Evaluated dynamically via [`ModelSelector.check_acceptance_thresholds()`](file:///e:/AI-Architecture-Decision-Intelligence-Platform/ml/src/optimization/model_selection.py#L125).
