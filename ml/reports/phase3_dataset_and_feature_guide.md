# ADIP — Phase 3 Dataset & Feature Engineering Guide

> **Author:** Anshika (AI/ML & Data Intelligence Lead)  
> **Project:** AI-Powered Architecture Decision Intelligence Platform (ADIP)  
> **Phase:** 3 — Data Strategy, Dataset Creation & Feature Architecture  
> **Status:** Completed & Operational  

---

## 1. Executive Summary

Software architecture decisions—such as choosing between a monolith vs. microservices, PostgreSQL vs. MongoDB, adding Redis cache, or deploying to Kubernetes—are traditionally made using developer intuition, rules of thumb, or costly trial-and-error.

The **AI-Powered Architecture Decision Intelligence Platform (ADIP)** transforms architecture selection into an **evidence-driven, quantitative, and explainable** discipline. 

**Phase 3** establishes the scientific and data foundation for this platform. It defines:
1. **The 5 Linked Relational Datasets** that decouple requirements, architectures, workloads, and outcomes.
2. **The 15 Data Sources** categorized into 5 distinct evidence types (provenance-aware).
3. **The Feature Engineering Universe**, translating architecture graphs (nodes, edges, call chains) and workload stress into machine learning feature matrices.
4. **Leakage-Safe Splitting and Data Governance** protocols.

---

## 2. Directory Layout & Related Files

All Phase 3 code, configurations, and data artifacts reside in the following structure:

```text
ADIP_Major_Project/
├── ml/
│   ├── configs/
│   │   ├── data.yaml                     # Registry of 15 sources, evidence types, provenance
│   │   └── features.yaml                 # 5-dataset schema specs, graph features & targets
│   ├── data/
│   │   ├── raw/                          # Untouched, isolated raw sources (15 subfolders)
│   │   │   ├── 01_zenodo/provenance_manifest.json
│   │   │   ├── 02_alibaba/provenance_manifest.json
│   │   │   ├── 03_techempower/provenance_manifest.json
│   │   │   ├── ...
│   │   │   └── adip_simulation_engine/provenance_manifest.json
│   │   ├── interim/                      # Cleaned, standardized intermediate data
│   │   ├── processed/                    # Feature-engineered per-source tables
│   │   └── external/                     # External pricing/taxonomies
│   ├── src/
│   │   ├── data/
│   │   │   ├── ingest.py                 # Multi-source ingestion & manifest generator
│   │   │   ├── validate.py               # Bounds check, schema audit & leakage detection
│   │   │   └── split.py                  # GroupKFold / GroupShuffleSplit by architecture_id
│   │   └── features/
│   │       ├── feature_registry.py       # Single source of truth for all column lists
│   │       └── build_features.py         # NetworkX graph metrics & interaction ratios
│   └── reports/
│       └── phase3_dataset_and_feature_guide.md  # [THIS DOCUMENT]
└── packages/
    └── shared-schemas/
        ├── requirements.schema.json      # JSON schema contract for Dataset A
        ├── architecture.schema.json      # JSON schema contract for Dataset B
        └── prediction.schema.json        # JSON schema contract for Dataset D & ML output
```

---

## 3. The 5-Dataset Architecture (*"Five Datasets, Not One Monolithic CSV"*)

Instead of forcing all variables into an unmaintainable single flat table, ADIP separates concerns into **5 linked relational datasets**, joined via `architecture_id` and `workload_id`.

```text
┌─────────────────────────────────┐       ┌─────────────────────────────────┐
│     Dataset A: Requirements     │       │     Dataset B: Architecture     │
│   (What the user asks for)      │       │      (What the system builds)   │
├─────────────────────────────────┤       ├─────────────────────────────────┤
│ • project_id (PK)               │       │ • architecture_id (PK)          │
│ • domain                        │       │ • architecture_pattern          │
│ • users, concurrency            │       │ • service_count, replica_count  │
│ • rps, peak_rps                 │       │ • database, cache, messaging    │
│ • latency_sla, availability_sla │       │ • deployment, cpu/memory_limit  │
│ • budget, team_size             │       │ • node_count, edge_count        │
└─────────────────────────────────┘       └────────────────┬────────────────┘
                                                           │
┌─────────────────────────────────┐                        │
│       Dataset C: Workload       │                        │
│   (Traffic hitting the system)  │                        │
├─────────────────────────────────┤                        │
│ • workload_id (PK)              │                        │
│ • rps, concurrency              │                        │
│ • read_write_ratio              │                        │
│ • data_size, request_size       │                        │
│ • workload_type, traffic_pattern│                        │
└────────────────┬────────────────┘                        │
                 │                                         │
                 ├────────────────────┬────────────────────┤
                 ▼                    ▼                    ▼
┌───────────────────────────────┐┌────────────────────────┐┌────────────────────────┐
│    Dataset D: Performance     ││    Dataset E: Cost     ││ Dataset D2: Reliability│
│   (How the system behaves)    ││(What it costs to run)  ││   (System resilience)  │
├───────────────────────────────┤├────────────────────────┤├────────────────────────┤
│ • experiment_id (PK)          ││ • architecture_id (FK) ││ • architecture_id (FK) │
│ • architecture_id (FK)        ││ • monthly_cost ($)     ││ • error_rate (%)       │
│ • workload_id (FK)            ││ • compute_cost ($)     ││ • availability_score   │
│ • latency p50, p90, p95, p99  ││ • database_cost ($)    ││ • mtbf (mean time fail)│
│ • throughput (RPS)            ││ • cache_cost ($)       ││                        │
│ • cpu (%), memory (MB)        ││                        ││                        │
└───────────────────────────────┘└────────────────────────┘└────────────────────────┘
```

### Dataset Field Dictionaries

#### Dataset A — Requirements (User Inputs)
- `project_id` *(String)*: Unique project reference.
- `domain` *(Categorical)*: `e-commerce`, `fintech`, `social_network`, `streaming`, `iot`, `healthcare`, `saas`.
- `users` *(Integer)*: Total registered active users.
- `concurrency` *(Integer)*: Peak simultaneous user sessions.
- `rps` & `peak_rps` *(Float)*: Average and burst requests per second.
- `data_size` *(Float)*: Total data volume in GB.
- `read_write_ratio` *(Float)*: Fraction of read traffic ($0.0 - 1.0$).
- `latency_sla` *(Float)*: Maximum tolerable latency target (ms).
- `availability_sla` *(Float)*: Target uptime percentage ($99.0\% - 99.999\%$).
- `budget` *(Float)*: Monthly infrastructure budget in USD ($).

#### Dataset B — Architecture (Structural Specs)
- `architecture_id` *(String)*: Unique candidate architecture identifier.
- `architecture_pattern` *(Categorical)*: `monolith`, `modular_monolith`, `microservices`, `event_driven`, `serverless`.
- `architecture_style` *(Categorical)*: `layered`, `hexagonal`, `cqrs`, `event_sourcing`, `pipeline`.
- `service_count` *(Integer)*: Number of independently deployable services ($1 - 100$).
- `database` *(Categorical)*: `postgres`, `mysql`, `mongodb`, `dynamodb`, `cassandra`, `redis_only`, `none`.
- `cache` *(Categorical)*: `none`, `redis`, `memcached`, `hazelcast`.
- `messaging` *(Categorical)*: `none`, `kafka`, `rabbitmq`, `aws_sqs`, `nats`.
- `api_style` *(Categorical)*: `rest`, `graphql`, `grpc`, `websocket`.
- `deployment` *(Categorical)*: `docker_compose`, `kubernetes`, `aws_ecs`, `aws_lambda`, `bare_metal_vm`.
- `replica_count` *(Integer)*: Horizontal container instances.
- `cpu_limit` & `memory_limit` *(Float)*: Hardware allocations per replica (vCPUs and GB RAM).
- `node_count` & `edge_count` *(Integer)*: Vertices and directed communication edges in the architecture graph.

#### Dataset C — Workload (Dynamic Traffic Profile)
- `workload_id` *(String)*: Workload identifier.
- `rps` *(Float)*: Applied request rate.
- `concurrency` *(Integer)*: Concurrent client connections.
- `read_write_ratio` *(Float)*: Read proportion ($0.0 - 1.0$).
- `data_size` *(Float)*: Database storage size in GB.
- `request_size` *(Float)*: Average payload size in KB.
- `workload_type` *(Categorical)*: `oltp`, `olap`, `read_heavy`, `write_heavy`, `balanced`, `streaming`.
- `traffic_pattern` *(Categorical)*: `steady`, `bursty`, `diurnal`, `exponential_spike`, `gradual_ramp`.

#### Dataset D — Performance (Observations / Ground Truth)
- `experiment_id` *(String)*: Unique benchmark or simulation run ID.
- `architecture_id` & `workload_id` *(Foreign Keys)*.
- `p50`, `p90`, `p95`, `p99` *(Float)*: Response latency percentiles in milliseconds.
- `throughput` *(Float)*: Successfully served requests per second (RPS).
- `cpu` *(Float)*: Average CPU utilization percentage ($0.0\% - 100.0\%$).
- `memory` *(Float)*: Memory utilization footprint in MB.
- `error_rate` *(Float)*: Percentage of failed requests ($0.0\% - 100.0\%$).
- `db_latency` *(Float)*: Query processing time at the persistence tier (ms).
- `cache_hit_rate` *(Float)*: Cache hit percentage ($0.0 - 1.0$).
- `network_latency` *(Float)*: Inter-service networking overhead (ms).

#### Dataset E — Cost (Infrastructure Economics)
- `monthly_cost` *(Float)*: Total estimated monthly cost in USD ($).
- `compute_cost` *(Float)*: EC2 / Fargate container runtime charges.
- `database_cost` *(Float)*: Managed database instance and storage fees.
- `cache_cost` *(Float)*: In-memory cache hosting cost.

---

## 4. Multi-Source Data Strategy & The 5 Evidence Types

Because no single public dataset covers the full architecture-to-cost spectrum, ADIP collects from **15 heterogeneous sources** grouped into **5 Evidence Types**:

| Evidence Type | Characteristics & Role | Included Sources |
|---|---|---|
| **Type A: Production Traces** | High ecological validity, unconstrained real-world behavior | **Alibaba Microservices Cluster Trace (v2021)**: Over 20,000 microservices call graphs, call rates, response times, and CPU/memory utilization. |
| **Type B: Controlled Benchmarks** | Repeatable, controlled measurements under varied parameters | • **Zenodo Microservices Benchmark**: Containerized CPU/memory/latency.<br>• **TechEmpower FrameworkBenchmarks**: Web throughput and DB query performance.<br>• **Barista Benchmarks**: Cold-start and scaling latency.<br>• **YCSB**: Key-value/DB read vs. write workloads.<br>• **TPC Benchmarks**: Standardized transaction/ACID performance.<br>• **AWS Price List API**: Real-world cloud hourly compute/DB/cache rates. |
| **Type C: Architecture Topologies** | Concrete dependency graphs and service topologies | • **Technical-Architectures-Large**: Graph topology specifications.<br>• **DeathStarBench**: Social Network, Hotel Reservation, Media microservices.<br>• **Train-Ticket**: Large 40+ service microservice benchmark.<br>• **Google Online Boutique**: 11-tier gRPC/Redis cloud-native application.<br>• **OpenTelemetry Demo**: Distributed tracing & error propagation. |
| **Type D: Knowledge / Text** | Unstructured architecture rationale and patterns | • **Software-Architecture Dataset**: Architecture trade-off text, ADRs, cloud docs. *(Used exclusively for RAG Knowledge Base + pgvector, excluded from numerical regression).* |
| **Type E: ADIP-Generated Data** | Direct, calibrated ground truth connecting custom graphs to outcomes | • **ADIP Controlled Experiments**: Locust/k6 load test runs on Docker/K8s.<br>• **ADIP SimPy Simulation**: Discrete-event queuing model under deterministic seeds. |

---

## 5. Feature Engineering: Transforming Architecture into Numbers

Raw software architecture diagrams cannot be fed directly into machine learning models. The **`ArchitectureFeatureBuilder`** ([ml/src/features/build_features.py](file:///c:/Users/hp/OneDrive/Desktop/Code/ADIP_Major_Project/ml/src/features/build_features.py)) extracts four feature families:

### 1. Categorical Architecture Encodings
Encoded via one-hot encoding or learned embeddings:
- `pattern`, `database`, `cache`, `messaging`, `api_style`, `deployment`, `cloud`.

### 2. Base Capacity Features
- `service_count`, `replica_count`, `cpu_limit`, `memory_limit`, `rps`, `concurrency`, `read_write_ratio`, `data_size`, `request_size`.

### 3. Graph Topology Features (NetworkX)
Software architectures are directed graphs $G = (V, E)$, where services are nodes and network calls are edges:
- **`graph_depth`**: Length of the longest call chain. Longer chains suffer compounding latency and higher tail risk.
- **`average_degree`**: Degree of inter-service coupling ($\frac{|E|}{|V|}$).
- **`max_fan_in`**: Highest in-degree across nodes. Detects bottlenecks and central choke points.
- **`max_fan_out`**: Highest out-degree across nodes. Detects cascading failure risks.
- **`critical_path_length`**: Cumulative latency across the synchronous critical path.
- **`architecture_complexity_score`**: Penalizes architectural sprawl:
  $$\text{Complexity} = (|V| \times 0.4) + (|E| \times 0.6) \times \left(1 + \frac{\text{max\_fan\_out}}{5}\right)$$

### 4. Workload Intensity & Interaction Ratios
- **`rps_per_service`**: $\frac{\text{RPS}}{\text{service\_count}}$ (Load density per microservice).
- **`concurrency_per_replica`**: $\frac{\text{Concurrency}}{\text{replica\_count}}$ (Queue pressure per container instance).
- **`data_per_request_ratio`**: $\frac{\text{Data Volume (MB)}}{\text{RPS}}$ (Network payload pressure).
- **`cache_capacity_coverage`**: Binary indicator ($1.0$ if cache is present, $0.0$ if all reads hit DB).

---

## 6. Machine Learning Model Mapping

Features from Datasets B & C and engineered features form the input vector ($X$). They train **5 specialized predictive models**:

| Model | Target Variables ($Y$) | Primary Algorithm | Optimization Objective |
|---|---|---|---|
| **Model 1: Latency** | $p_{50}, p_{95}, p_{99}$ (ms) | XGBoost / Gradient Boosting Regressor | Minimize RMSE |
| **Model 2: Throughput** | Sustained RPS | Random Forest / XGBoost Regressor | Minimize RMSE |
| **Model 3: Resources** | CPU Utilization (%) & Memory (MB) | Gradient Boosting Regressor | Minimize MAE |
| **Model 4: Cost** | Monthly Cloud Bill ($ USD) | Gradient Boosting + AWS Pricing Rules | Minimize MAPE |
| **Model 5: Reliability** | Error Rate (%) & Failure Probability | Random Forest Classifier / Regressor | Minimize Log-Loss / RMSE |

---

## 7. Data Governance & Integrity Protocols

### A. The "Don't Combine Immediately" Rule
Raw datasets must never be dumped into one blended CSV:
1. **Raw Stage:** Preserved untouched in `ml/data/raw/{source_name}` with an immutable `provenance_manifest.json`.
2. **Interim Stage:** Cleaned and standardized per source (units normalized to ms, RPS, GB).
3. **Unified Stage:** Joined only after independent validation passes.

### B. Group-Based Splitting (Preventing Train/Test Leakage)
- **Problem with naive splitting:** If tests from the *same* architecture exist in both Train and Test sets, the model simply memorizes that architecture.
- **ADIP Solution ([ml/src/data/split.py](file:///c:/Users/hp/OneDrive/Desktop/Code/ADIP_Major_Project/ml/src/data/split.py)):**  
  Uses `GroupShuffleSplit` on `architecture_id`:
  - **70% of Architectures:** Training Set.
  - **15% of Architectures:** Validation Set (Hyperparameter tuning).
  - **15% of Architectures:** Test Set (Completely unseen architectures).
  This guarantees that models are tested on their ability to **generalize to brand new architecture designs**.

### C. Validation & Sanity Guardrails ([ml/src/data/validate.py](file:///c:/Users/hp/OneDrive/Desktop/Code/ADIP_Major_Project/ml/src/data/validate.py))
- Non-negative latency check: All latency metrics must satisfy $p > 0$ ms.
- Percentage bound check: CPU, availability, and error rates must be strictly within $[0.0, 100.0]\%$.
- Leakage check: Ensures target outputs (e.g., $p_{99}$ latency or cost) never appear in the input feature matrix $X$.

---

## 8. Summary of Phase 3 Deliverables

| Deliverable | File Path | Status |
|---|---|---|
| Data Source Registry | [ml/configs/data.yaml](file:///c:/Users/hp/OneDrive/Desktop/Code/ADIP_Major_Project/ml/configs/data.yaml) | Verified & Configured |
| 5-Dataset & Feature Specifications | [ml/configs/features.yaml](file:///c:/Users/hp/OneDrive/Desktop/Code/ADIP_Major_Project/ml/configs/features.yaml) | Verified & Configured |
| Ingestion & Manifest Pipeline | [ml/src/data/ingest.py](file:///c:/Users/hp/OneDrive/Desktop/Code/ADIP_Major_Project/ml/src/data/ingest.py) | Tested & Passing |
| Validation & Quality Audit Module | [ml/src/data/validate.py](file:///c:/Users/hp/OneDrive/Desktop/Code/ADIP_Major_Project/ml/src/data/validate.py) | Tested & Passing |
| Group Architecture Splitting Module | [ml/src/data/split.py](file:///c:/Users/hp/OneDrive/Desktop/Code/ADIP_Major_Project/ml/src/data/split.py) | Tested & Passing |
| Feature Registry Contract | [ml/src/features/feature_registry.py](file:///c:/Users/hp/OneDrive/Desktop/Code/ADIP_Major_Project/ml/src/features/feature_registry.py) | Verified |
| NetworkX Graph Feature Builder | [ml/src/features/build_features.py](file:///c:/Users/hp/OneDrive/Desktop/Code/ADIP_Major_Project/ml/src/features/build_features.py) | Tested & Passing |
| Shared Schema Contracts | [packages/shared-schemas/](file:///c:/Users/hp/OneDrive/Desktop/Code/ADIP_Major_Project/packages/shared-schemas/) | Formal Schemas Created |
| Dataset & Feature Engineering Guide | [ml/reports/phase3_dataset_and_feature_guide.md](file:///c:/Users/hp/OneDrive/Desktop/Code/ADIP_Major_Project/ml/reports/phase3_dataset_and_feature_guide.md) | Documented |
