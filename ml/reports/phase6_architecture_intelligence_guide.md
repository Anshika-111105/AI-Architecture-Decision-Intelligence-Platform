# Phase 6 — Architecture Intelligence Technical Guide
**Author & Deliverable Lead:** Anshika (AI/ML & Data Intelligence Lead)  
**Collaborators:** Akriti (Application Lead), Ananya (Model Evaluation Lead), Shruti (DevOps Lead)  
**Status:** Complete & Validated (76/76 Tests Passing)  
**Specification Reference:** `docs/Phase6_Architecture_Intelligence.docx`

---

## 1. Executive Summary & Pipeline Flow

Phase 6 implements the core conversion engine of the **Architecture Intelligence** layer. It bridges the visual diagram built by the user in the React Flow canvas with the mathematical graph representation required for structural validation, simulation, and downstream ML prediction.

### Three Forms of an Architecture (Section 1)
1. **Visual Form:** Built interactively by the user in React Flow (components, connections, and configurations).
2. **Computational Form:** NetworkX directed graph (`DiGraph`) on the backend for structural validation, cycle detection, and topological metric extraction.
3. **ML-Ready Form:** A strictly bounded, 31-dimension numerical and encoded feature vector matching **Dataset B (Architecture)** and `feature_registry.py`.

```
[React Flow Canvas (Akriti)]
              │
              ▼
   [ArchitectureGraph Schema (Anshika)]
              │
              ▼
  [NetworkX DiGraph Extractor (Anshika)]
   ├── Structural Counts: service_count, node_count, edge_count, replica_count, cpu, memory
   └── Graph Metrics: graph_depth, max_fan_in, max_fan_out, critical_path, complexity
              │
              ▼
[MLArchitectureRepresentation (Anshika)]  ◄─── [Normalized Requirements (Phase 5)]
   ├── Fuses Graph + Workload Dimensions
   ├── Computes Interactions: rps_per_service, concurrency_per_replica, cache_coverage
   ├── Versioned Categorical Encoding with Unseen Category Safety
   └── Zero Target Leakage Guard
              │
              ▼
[Standardized Feature Vector (1D float32) / DataFrame]
              │
              ▼
[ML Prediction Models: Latency, Throughput, Cost, Reliability]
```

---

## 2. Core Modules Implemented (Anshika)

All Phase 6 intelligence modules are located inside `ml/src/architecture/`:

| Module | File | Responsibilities |
|---|---|---|
| **Schemas** | [`schemas.py`](file:///c:/Users/hp/OneDrive/Desktop/Code/ADIP_Major_Project/ml/src/architecture/schemas.py) | Pydantic v2 schemas for nodes (`ArchitectureComponent`), edges (`ArchitectureDependency`), and complete graphs (`ArchitectureGraph`). Auto-derives structural counts and standardizes technology names. |
| **Graph Extractor** | [`graph_extractor.py`](file:///c:/Users/hp/OneDrive/Desktop/Code/ADIP_Major_Project/ml/src/architecture/graph_extractor.py) | NetworkX DiGraph builder, React Flow adapter, and topological metric extractor (`graph_depth`, `average_degree`, `max_fan_in`, `max_fan_out`, `critical_path_length`, `complexity_score`, cycle detection). |
| **Representation** | [`representation.py`](file:///c:/Users/hp/OneDrive/Desktop/Code/ADIP_Major_Project/ml/src/architecture/representation.py) | Fuses architecture features with Phase 5 requirements, computes intensity interactions, provides versioned categorical encoding with unseen category fallback, and enforces zero target leakage. |
| **Package Init** | [`__init__.py`](file:///c:/Users/hp/OneDrive/Desktop/Code/ADIP_Major_Project/ml/src/architecture/__init__.py) | Clean exports for backend API consumption. |
| **Automated Tests** | [`test_architecture_intelligence.py`](file:///c:/Users/hp/OneDrive/Desktop/Code/ADIP_Major_Project/ml/tests/architecture/test_architecture_intelligence.py) | 14 comprehensive tests covering schemas, React Flow adaptation, graph metrics, encoding safety, and zero target leakage. |

---

## 3. Specification Table 9: Extracted Feature Schema

The engine extracts and aligns the architecture features into the **31 canonical columns** defined in Phase 4 `ALL_FEATURE_COLUMNS`:

| Feature Group | Feature Name | Type | Extraction Logic / Formula |
|---|---|---|---|
| **Pattern & Style** | `architecture_pattern` | Categorical | `monolith`, `modular_monolith`, `microservices`, `event_driven`, `serverless` |
| | `architecture_style` | Categorical | `layered`, `hexagonal`, `cqrs`, `event_sourcing`, `pipeline`, `service_oriented` |
| | `api_style` | Categorical | `rest`, `graphql`, `grpc`, `websocket` |
| **Technology Choices** | `database` | Categorical | Primary database extracted from components (`postgres`, `mongodb`, `mysql`, `dynamodb`, `cassandra`, `none`) |
| | `cache` | Categorical | Primary cache extracted (`redis`, `memcached`, `hazelcast`, `none`) |
| | `messaging` | Categorical | Primary message broker (`kafka`, `rabbitmq`, `aws_sqs`, `nats`, `none`) |
| | `deployment` | Categorical | Deployment style (`docker_compose`, `kubernetes`, `aws_ecs`, `aws_lambda`, `bare_metal_vm`) |
| | `cloud` | Categorical | Cloud provider (`aws`, `gcp`, `azure`, `on_premise`) |
| | `workload_type` | Categorical | Transferred from Phase 5 requirement (`oltp`, `olap`, `read_heavy`, `write_heavy`, `balanced`, `streaming`) |
| | `traffic_pattern` | Categorical | Workload characteristic (`steady`, `bursty`, `diurnal`, `exponential_spike`) |
| **Size & Capacity** | `service_count` | Numerical ($\ge 1$) | Count of application service / monolith components |
| | `replica_count` | Numerical ($\ge 1$) | Sum of all component replicas |
| | `cpu_limit` | Numerical | Total aggregated CPU cores across all replicas |
| | `memory_limit` | Numerical | Total aggregated Memory in GB across all replicas |
| | `node_count` | Numerical | Total nodes in the architecture graph |
| | `edge_count` | Numerical | Total directed dependencies in the architecture graph |
| **Workload Dimensions** | `rps` | Numerical | Target request rate from Phase 5 requirement |
| | `concurrency` | Numerical | Concurrent active users / sessions |
| | `read_write_ratio` | Numerical $[0.0, 1.0]$ | Fraction of read operations |
| | `data_size` | Numerical | Data storage volume in GB |
| | `request_size` | Numerical | Average request payload size in KB |
| **Graph Topology (NetworkX)** | `graph_depth` | Integer ($\ge 0$) | Longest dependency path in DAG (`nx.dag_longest_path_length`) |
| | `average_degree` | Float | Mean connections per node: $\frac{\text{edges}}{\text{nodes}}$ |
| | `max_fan_in` | Integer | Maximum incoming calls to any single component (bottleneck detector) |
| | `max_fan_out` | Integer | Maximum outgoing calls from any single component (fan-out orchestrator) |
| | `critical_path_length` | Float | Estimated critical execution pipeline depth: $\text{graph\_depth} \times 1.5$ |
| | `architecture_complexity_score` | Float | $(\text{nodes} \times 0.4) + (\text{edges} \times 0.6) \times (1.0 + \frac{\text{max\_fan\_out}}{5.0})$ |
| **Interaction Features** | `rps_per_service` | Float | $\frac{\text{rps}}{\max(\text{service\_count}, 1)}$ |
| | `concurrency_per_replica` | Float | $\frac{\text{concurrency}}{\max(\text{replica\_count}, 1)}$ |
| | `data_per_request_ratio` | Float | $\frac{\text{data\_size} \times 1024.0}{\max(\text{rps}, 1.0)}$ |
| | `cache_capacity_coverage` | Float $[0.0, 1.0]$ | $1.0$ if cache is present, $0.0$ if `none` |

---

## 4. Zero Target Leakage Protocol (Section 9.2)

Per Section 9.2 of the Phase 6 specification:
1. **Design-Time Input Only:** Architecture features represent static, pre-deployment configurations.
2. **Forbidden Outcome Metrics:** The extractor and encoder enforce that no measured runtime metric (e.g., `latency`, `throughput`, `p50`, `p95`, `p99`, `monthly_cost`, `error_rate`, `observed_cache_hit_rate`) can enter the architecture representation.
3. If an input payload contains forbidden outcome fields, `MLArchitectureRepresentation` throws an immediate `ValueError` preventing data contamination.

---

## 5. Review Records & Handoff Guidelines

### For Teammate Akriti (Application Lead):
When the user saves or runs predictions on an architecture in React Flow, pass the canvas payload to `MLArchitectureRepresentation`:

```python
from ml.src.architecture import ArchitectureGraphExtractor, MLArchitectureRepresentation
from ml.src.requirements.schemas import NormalizedRequirement

encoder = MLArchitectureRepresentation()

# 1. Validate graph structure (cycles, orphans, entry points)
G, arch_model = ArchitectureGraphExtractor.to_networkx(react_flow_json)
validation = ArchitectureGraphExtractor.validate_graph_structure(G)
if not validation["is_valid"]:
    return {"status": "error", "errors": validation["errors"]}

# 2. Extract ML feature vector (combining with Phase 5 requirements)
feature_df = encoder.build_feature_dataframe(arch_model, validated_requirements)
feature_vector = encoder.encode_feature_vector(feature_df.iloc[0].to_dict())
```

### For Teammate Ananya (Model Evaluation Lead — Section 10.1 Review):
- **Feature Consistency:** Benchmarks from standard datasets (DeathStarBench, Train-Ticket) and user-built canvas architectures generate identical 31-dimension feature vectors.
- **Unseen Category Safety (Section 12):** If a user selects an unsupported or novel technology, the encoder gracefully maps it to default category index `0` rather than raising unhandled exceptions or breaking ML inference.
- **Versioned Encoder:** Encoder specification version `1.0.0` is registered alongside Phase 4 datasets.

### For Teammate Shruti (DevOps Lead — Section 10.2 Scalability Review):
- Single points of failure (nodes where `max_fan_in` is concentrated) and deep request chains (`graph_depth > 5`) are flagged during graph extraction.
- Total replica and resource bounds (`cpu_limit`, `memory_limit`) are aggregated for container deployment sizing.

---

## 6. Test Suite Results

- **Phase 6 Tests:** **14 / 14 Passed (100%)**
- **Total ML Suite (Phases 3, 4, 5, 6):** **76 / 76 Passed (100% Pass Rate)**
