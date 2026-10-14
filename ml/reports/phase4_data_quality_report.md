# ADIP — Phase 4: Data Quality & Leakage Prevention Report

**Document Version:** 1.0  
**Phase:** 4 — Data Quality & Leakage Prevention  
**Author / Lead:** Anshika (AI/ML & Data Intelligence Lead)  
**Independent Reviewer:** Ananya (ML Reviewer & Methodology Auditor)  
**Supporting Team:** Akriti (Full-Stack & Database), Shruti (Infrastructure & DevOps)  
**Date:** October 2026  
**Status:** Approved & Validated (Release Gate Passed)  

---

## 1. Executive Summary & Purpose

Phase 3 defined where ADIP's data originates and organized it into five linked datasets:
- **Dataset A — Requirements** (Constraints, SLAs, budgets)
- **Dataset B — Architecture** (Patterns, databases, caches, messaging, deployments)
- **Dataset C — Workload** (RPS, concurrency, read/write ratios, request sizes)
- **Dataset D — Performance** (Latency percentiles $p_{50}, p_{90}, p_{95}, p_{99}$, throughput)
- **Dataset E — Cost** (Monthly USD expenditures across compute, storage, network)

**Phase 4 answers the decisive scientific question: Can this data be trusted to train surrogate machine learning models?**

Treating data quality and leakage prevention as an explicit, stand-alone project phase—rather than an informal sub-step of data cleaning—ensures that:
1. **Zero Data Leakage:** Models are evaluated under realistic prediction constraints where runtime telemetry is unknown.
2. **Physical Law Compliance:** Unphysical artifacts (such as inverted latency percentiles $p_{50} > p_{99}$ or negative cloud costs) are strictly eliminated.
3. **Rigorous Independent Review:** Authoring validation checks (Anshika) is separated from reviewing methodology (Ananya), guaranteeing high research and engineering credibility.

---

## 2. Validation Pipeline Architecture

The automated validation pipeline processes datasets through sequential validation gates before promoting records to `ml/data/unified/`:

```
Raw / Ingested Sources (Types A–E)
               │
               ▼
   [1. Schema Validation]       ──► Primary/foreign keys verified, zero orphaned records
               │
               ▼
   [2. Missing-Value Audit]     ──► Expected (optional) vs. unexpected gaps classified
               │
               ▼
   [3. Duplicate Detection]     ──► Exact duplicates and configuration near-duplicates isolated
               │
               ▼
   [4. Outlier Analysis]        ──► Non-parametric IQR & MAD profiling; saturation tails preserved
               │
               ▼
   [5. Physical Boundary Laws]  ──► Percentile monotonicity (p50 ≤ p90 ≤ p95 ≤ p99) & ratio bounds
               │
               ▼
   [6. Leakage Guard]           ──► 3-Tier feature classification & GroupShuffleSplit isolation
               │
               ▼
   [Approved Dataset v1.0]      ──► Cleared for Phase 5 Model Training & Requirement Intelligence
```

---

## 3. Section 6: Data Quality Audit Findings (Anshika)

Implemented in [`ml/src/data/quality_checker.py`](ml/src/data/quality_checker.py) and profiled interactively in [`ml/notebooks/02_data_quality.ipynb`](ml/notebooks/02_data_quality.ipynb).

### 3.1 Schema & Key Integrity (Section 6.1)
- **Primary Keys Checked:** `architecture_id`, `workload_id`, `project_id`, `experiment_id`.
- **Relational Joins:** Verified joins across Datasets B, C, D, and E on composite keys `(architecture_id, workload_id)`. Zero orphaned records were detected.
- **Null Primary Keys:** 0 null entries across all active tables.
- **Status:** **PASSED**

### 3.2 Missing-Value Analysis & Remediation (Section 6.2)
Missingness was categorized into two distinct classes:
1. **Expected Missingness (Optional Architectural Components):**
   - Fields such as `cache` and `messaging` were missing in ~25% and ~30% of rows respectively.
   - **Root Cause:** The architecture pattern or benchmark design intentionally omits caching (direct database access) or messaging (synchronous REST/gRPC).
   - **Remediation Strategy:** Imputed with the explicit domain category `"none"`. Numerical ratios (e.g. `cache_hit_rate`) default to `0.0`.
2. **Unexpected Missingness (Mandatory Fields):**
   - Critical fields (`rps`, `concurrency`, `p99`, `total_monthly_cost`) exhibited 0.0% missingness.
- **Status:** **PASSED**

### 3.3 Duplicate & Near-Duplicate Auditing (Section 6.3)
- **Exact Duplicates:** 0 exact duplicate rows across all ingested records.
- **Primary Key Collisions:** 0 primary key collisions.
- **Configuration Near-Duplicates:** Identified rows with identical structural configurations and workload parameters resulting from repeated empirical benchmark trials.
  - **Remediation:** Retained for statistical variance estimation, but strictly quarantined to remain on the same side of the train/test split (see Section 4.4).
- **Status:** **PASSED**

### 3.4 Outlier Analysis & Heavy-Tailed Distributions (Section 6.4)
Traditional Gaussian 3-sigma filters fail on software performance data because response times are heavily skewed and log-normal or Pareto distributed.

We implemented robust non-parametric outlier boundaries:
$$\text{IQR} = Q_3 - Q_1$$
$$\text{Lower Bound} = Q_1 - 2.5 \times \text{IQR}, \quad \text{Upper Bound} = Q_3 + 2.5 \times \text{IQR}$$
$$\text{MAD} = \text{median}(|x_i - \text{median}(x)|)$$

**Outlier Summary Statistics ($N=1,500$ observations):**

| Target Metric | Median | IQR | Upper Threshold (2.5× IQR) | Outlier Count | Outlier % | Action Taken |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **$p_{50}$ Latency** | 20.60 ms | 19.25 ms | 81.73 ms | 175 | 11.67% | Preserved (Queuing saturation) |
| **$p_{90}$ Latency** | 33.50 ms | 36.38 ms | 149.56 ms | 209 | 13.93% | Preserved (Queuing saturation) |
| **$p_{95}$ Latency** | 45.93 ms | 59.07 ms | 237.24 ms | 236 | 15.73% | Preserved (High fan-out tail) |
| **$p_{99}$ Latency** | 85.49 ms | 142.59 ms | 553.04 ms | 249 | 16.60% | Preserved (Dean & Barroso tail effect) |
| **Monthly Cost** | \$6,313.48 | \$8,851.55 | \$34,527.27 | 38 | 2.53% | Preserved (Large-scale cluster topologies) |

> **Key Engineering Decision:** Outliers were audited and confirmed to be genuine operational knees of the queue saturation curve rather than sensor corruption. They are preserved for training so surrogate models learn tail risks.

- **Status:** **PASSED & REVIEWED**

### 3.5 Range Validation & Physical Boundary Invariants (Section 6.5)
Every record must conform to non-negotiable physical laws:
- **Percentile Monotonicity Law:**
  $$p_{50} \le p_{90} \le p_{95} \le p_{99}$$
  *Result:* **0 violations** across all records.
- **Ratio Bound Invariant:**
  $$\text{read\_write\_ratio} \in [0.0, 1.0], \quad \text{error\_rate} \in [0.0, 1.0], \quad \text{cache\_hit\_rate} \in [0.0, 1.0]$$
  *Result:* **0 violations**.
- **Positivity Invariant:**
  $$\text{RPS} > 0, \quad \text{concurrency} > 0, \quad \text{throughput} > 0, \quad \text{users} > 0$$
  *Result:* **0 violations**.
- **Non-Negative Cost Invariant:**
  $$\text{total\_monthly\_cost} \ge 0, \quad \text{latency} \ge 0$$
  *Result:* **0 violations**.
- **Status:** **PASSED (100% Invariant Compliance)**

### 3.6 Categorical Controlled Vocabulary (Section 6.6)
Validated all categorical dimensions against the standardized controlled vocabulary in [`features.yaml`](ml/configs/features.yaml):
- `architecture_pattern`: `["monolith", "modular_monolith", "microservices", "event_driven", "serverless"]`
- `database`: `["postgres", "mysql", "mongodb", "dynamodb", "cassandra", "redis_only", "none"]`
- `cache`: `["none", "redis", "memcached", "hazelcast"]`
- `messaging`: `["none", "kafka", "rabbitmq", "aws_sqs", "nats"]`
- `deployment`: `["docker_compose", "kubernetes", "aws_ecs", "aws_lambda", "bare_metal_vm"]`
- `cloud`: `["aws", "gcp", "azure", "on_premise"]`
- *Result:* **0 unrecognized or misspelled categories**.
- **Status:** **PASSED**

---

## 4. Section 7: Leakage Detection & Isolation Report (Anshika)

Implemented in [`ml/src/data/leakage_guard.py`](ml/src/data/leakage_guard.py).

### 4.1 Strict 3-Tier Feature Classification (Section 7.2)
Every feature in the platform is formally assigned to one of three tiers:

```
[Tier 1: USER_SUPPLIED]      ──► Target RPS, concurrency, budget, SLAs, domain (Valid Input)
[Tier 2: DERIVED_STRUCTURAL]  ──► Graph depth, fan-out, replica counts, complexity (Valid Input)
─────────────────────────────────────────────────────────────────────────────────────────────
[Tier 3: OBSERVED_OUTCOMES]   ──► p99, throughput, CPU load, monthly cost (QUARANTINED AS TARGETS)
```

- **Enforcement Rule:** No column from Tier 3 (`OBSERVED_OUTCOMES`) is ever allowed into the feature matrix $X$ at training or prediction time.
- **Audit Result:** 16 candidate features audited; 0 observed outcomes present in $X$.
- **Status:** **PASSED**

### 4.2 Target Leakage Audit per Surrogate Model (Section 7.1)
Target leakage occurs when a feature restates or directly derives from the prediction target.

| Surrogate Model | Prediction Target | Strictly Prohibited Features | Audit Finding |
| :--- | :--- | :--- | :---: |
| **Latency Model** | $p_{99}$ Response Time | $p_{50}, p_{90}, p_{95}$, `db_latency`, `observed_cache_hit_rate` | **0 Leaks (PASSED)** |
| **Throughput Model** | Sustained Throughput | `error_rate`, $p_{50}, p_{99}$, `failed_requests` | **0 Leaks (PASSED)** |
| **Cost Model** | Total Monthly Cost | `compute_cost`, `database_cost`, `storage_cost`, `network_cost` | **0 Leaks (PASSED)** |
| **Reliability Model** | SLA Availability Score | `observed_error_rate_pct`, `unplanned_downtime_minutes` | **0 Leaks (PASSED)** |
| **Scalability Model** | Headroom Multiplier | `saturation_point_observed_rps` | **0 Leaks (PASSED)** |

- **Status:** **PASSED**

### 4.3 Train/Test Contamination & Group-Based Splitting (Section 7.4)
Random row-level splitting causes **Architectural Contamination**: the model memorizes an architecture configuration in the training fold and evaluates on a slightly perturbed workload of the same architecture in the test fold.

- **Mitigation:** Enforced [`ArchitectureDataSplitter`](ml/src/data/split.py) using `GroupShuffleSplit` on `architecture_id`.
- **Split Breakdown:**
  - **Train Set (70%):** 1,049 rows (1,049 unique architectures)
  - **Validation Set (15%):** 226 rows (226 unique architectures)
  - **Test Set (15%):** 225 rows (225 unique architectures)
- **Overlap Audit:**
  $$\text{Train} \cap \text{Test} = \emptyset, \quad \text{Train} \cap \text{Val} = \emptyset, \quad \text{Val} \cap \text{Test} = \emptyset$$
  **Zero architectural overlap** across all three partitions.
- **Status:** **PASSED**

### 4.4 Temporal Leakage Verification (Section 7.3)
For time-series telemetry (e.g. Alibaba production cluster traces), random splitting causes future information to leak into past predictions.
- **Check Enforced:** $\max(\text{Train Timestamp}) \le \min(\text{Test Timestamp})$.
- **Audit Result:** Chronological sorting and time-based splitting verified that training windows strictly precede evaluation windows.
- **Status:** **PASSED**

---

## 5. Automated Pytest Test Suite Results

The validation suite is fully automated in [`ml/tests/data/`](ml/tests/data/) and runs automatically during continuous integration:

```text
ml/tests/data/test_leakage_guard.py   ...... 11 PASSED (100%)
ml/tests/data/test_quality_checker.py ...... 16 PASSED (100%)
============================= 27 passed in 4.45s ==============================
```

### Test Case Breakdown

| Test File | Test Name | Invariant / Property Verified | Status |
| :--- | :--- | :--- | :---: |
| `test_quality_checker.py` | `test_schema_valid` | Key presence and correct structure | **PASSED** |
| `test_quality_checker.py` | `test_schema_missing_primary_key` | Catches missing mandatory ID keys | **PASSED** |
| `test_quality_checker.py` | `test_schema_null_primary_keys` | Catches null primary key entries | **PASSED** |
| `test_quality_checker.py` | `test_missing_values_expected_optional` | Categorizes optional component missingness | **PASSED** |
| `test_quality_checker.py` | `test_missing_values_unexpected_required` | Flags unexpected gaps in telemetry | **PASSED** |
| `test_quality_checker.py` | `test_exact_duplicates_detected` | Flags identical ingested records | **PASSED** |
| `test_quality_checker.py` | `test_primary_key_collision_detected` | Catches primary key collisions | **PASSED** |
| `test_quality_checker.py` | `test_outlier_detection_iqr` | Accurately identifies IQR boundaries | **PASSED** |
| `test_quality_checker.py` | `test_physical_invariants_valid` | Asserts compliance on clean data | **PASSED** |
| `test_quality_checker.py` | `test_percentile_monotonicity_violation` | Catches unphysical $p_{50} > p_{95}$ | **PASSED** |
| `test_quality_checker.py` | `test_ratio_bounds_violation` | Catches ratios outside $[0.0, 1.0]$ | **PASSED** |
| `test_quality_checker.py` | `test_negative_cost_violation` | Catches negative monthly dollar costs | **PASSED** |
| `test_quality_checker.py` | `test_negative_rps_violation` | Catches non-positive request rates | **PASSED** |
| `test_quality_checker.py` | `test_categoricals_valid` | Conforms to controlled vocabulary | **PASSED** |
| `test_quality_checker.py` | `test_categoricals_invalid_spelling` | Catches misspelled architectural categories | **PASSED** |
| `test_quality_checker.py` | `test_full_quality_suite` | 100% score on production data | **PASSED** |
| `test_leakage_guard.py` | `test_feature_tier_classification` | Assigns User / Structural / Outcome tiers | **PASSED** |
| `test_leakage_guard.py` | `test_feature_matrix_clean` | Approves clean input feature matrices | **PASSED** |
| `test_leakage_guard.py` | `test_feature_matrix_leaked_outcomes` | Blocks runtime outcomes in $X$ | **PASSED** |
| `test_leakage_guard.py` | `test_target_leakage_clean` | Approves target-independent features | **PASSED** |
| `test_leakage_guard.py` | `test_target_leakage_detected_latency` | Blocks $p_{50}$ in $p_{99}$ latency model | **PASSED** |
| `test_leakage_guard.py` | `test_target_leakage_detected_cost` | Blocks component costs in cost model | **PASSED** |
| `test_leakage_guard.py` | `test_train_test_group_isolation_clean` | Asserts 0 architecture overlap | **PASSED** |
| `test_leakage_guard.py` | `test_train_test_contamination_detected` | Flags cross-split group contamination | **PASSED** |
| `test_leakage_guard.py` | `test_temporal_leakage_valid` | Verifies chronological ordering | **PASSED** |
| `test_leakage_guard.py` | `test_temporal_leakage_detected` | Catches training on future data | **PASSED** |
| `test_leakage_guard.py` | `test_full_leakage_audit_approved` | Formally certifies `APPROVED_LEAKAGE_FREE` | **PASSED** |

---

## 6. Section 9: Independent Methodology Review Checklist (Ananya)

The independent review evaluates the statistical and experimental soundness of Anshika’s implementation:

| Review Area | Methodological Standard | Validation Status | Reviewer Notes |
| :--- | :--- | :---: | :--- |
| **Train/Test Splitting** | Grouped by `architecture_id` using `GroupShuffleSplit` (not random rows); zero architecture overlap between folds. | **VERIFIED** | Clean 70/15/15 partition; 0 shared keys. |
| **Preprocessing Isolation** | All scaling, one-hot encoding, and imputations fitted strictly on training folds; test folds only transformed. | **VERIFIED** | Documented pipeline prevents data snooping. |
| **Cross-Validation** | GroupKFold used for cross-validation; related architectures stay within single folds. | **VERIFIED** | Group boundaries preserved. |
| **Target Leakage** | Prohibited features quarantined per target model; 3-tier classification enforced. | **VERIFIED** | No Tier 3 outcomes present in $X$. |
| **Temporal Integrity** | Time-series traces partitioned chronologically ($\max(\text{train}) \le \min(\text{test})$). | **VERIFIED** | Chronological ordering holds for temporal sources. |
| **Physical Sanity** | Percentile monotonicity ($p_{50} \le p_{90} \le p_{95} \le p_{99}$) and ratio bounds enforced. | **VERIFIED** | 100% compliance across all records. |

---

## 7. Approval & Sign-Off Certification

```text
================================================================================
                    ADIP PHASE 4 QUALITY GATE CERTIFICATION
================================================================================
Dataset Version Tag:        v1.0-approved
Lead Engineer:              Anshika (AI/ML & Data Intelligence Lead)
Independent ML Reviewer:    Ananya (ML Reviewer & Methodology Auditor)
Quality Score:              100.0%
Quality Status:             PASSED
Leakage Status:             APPROVED_LEAKAGE_FREE
Physical Law Invariants:    100% COMPLIANT (0 Violations)
Automated Tests:            27 / 27 PASSED (100% Pass Rate)

APPROVAL DECISION:
[X] APPROVED: Dataset version v1.0-approved is certified free of target leakage,
    contamination, and physical violations, and is formally cleared for
    Phase 5 (Requirement Intelligence) and Surrogate Model Training.

Signed: Anshika (Lead) & Ananya (Reviewer)
================================================================================
```

---

## 8. Next Steps (Phase 5 Handshake)

With dataset version `v1.0-approved` formally certified and locked:
1. **Phase 5: Requirement Intelligence:** Implement the natural language and form-based requirement parsing pipeline (extracting target RPS, concurrency, latency SLAs, and budgets).
2. **Surrogate ML Model Training:** Begin training Gradient Boosting (XGBoost / LightGBM) and Multi-Layer Perceptrons on `v1.0-approved` using the leakage-safe feature matrices.
