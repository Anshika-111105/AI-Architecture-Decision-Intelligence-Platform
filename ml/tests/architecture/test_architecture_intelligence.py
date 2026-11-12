"""
ADIP Phase 6 Architecture Intelligence Automated Test Suite
Lead Deliverable — Anshika (AI/ML & Data Intelligence Lead)

Comprehensive tests covering:
  - Architecture schema validation, component inference, and derived counts
  - NetworkX graph construction and React Flow canvas conversion
  - Graph topological metrics (depth, average degree, fan-in/fan-out, critical path, complexity)
  - Graph structural validation (cycle detection, isolated nodes, entry points)
  - ML-compatible architecture representation and column alignment with ALL_FEATURE_COLUMNS
  - Unseen category safety and categorical encoding versioning
  - Zero target leakage verification (Section 9.2)
  - Deterministic reproducibility (Section 10.1 & Section 12)
"""

import pytest
import numpy as np
import pandas as pd
import networkx as nx
from pydantic import ValidationError

from ml.src.architecture.schemas import (
    ArchitectureGraph,
    ArchitectureComponent,
    ArchitectureDependency,
    ComponentCategory,
    ComponentType,
)
from ml.src.architecture.graph_extractor import ArchitectureGraphExtractor
from ml.src.architecture.representation import MLArchitectureRepresentation
from ml.src.requirements.schemas import NormalizedRequirement
from ml.src.features.feature_registry import ALL_FEATURE_COLUMNS


# =============================================================================
# 1. Architecture Schema & Component Tests (Section 5)
# =============================================================================
class TestArchitectureSchemas:
    """Tests Pydantic models for architecture components, edges, and derived fields."""

    def test_component_category_inference(self):
        """Infers category automatically from component type."""
        c_gw = ArchitectureComponent(id="gw", type="api_gateway")
        c_db = ArchitectureComponent(id="db", type="database", technology="postgresql")
        c_cache = ArchitectureComponent(id="rd", type="cache", technology="redis")
        c_broker = ArchitectureComponent(id="kf", type="message_broker", technology="kafka")
        c_svc = ArchitectureComponent(id="svc", type="service")

        assert c_gw.category == ComponentCategory.ENTRY.value
        assert c_db.category == ComponentCategory.DATA.value
        assert c_cache.category == ComponentCategory.PERFORMANCE.value
        assert c_broker.category == ComponentCategory.COMMUNICATION.value
        assert c_svc.category == ComponentCategory.APPLICATION.value

    def test_dependency_alias_support(self):
        """Supports both ('from', 'to') and ('source', 'target') edge keys."""
        dep1 = ArchitectureDependency(**{"from": "gw", "to": "svc"})
        dep2 = ArchitectureDependency(source="svc", target="db")

        assert dep1.source == "gw"
        assert dep1.target == "svc"
        assert dep2.source == "svc"
        assert dep2.target == "db"

    def test_derived_counts_and_technologies(self):
        """Guarantees derived counts (nodes, edges, services, replicas, cpu) match components."""
        graph_data = {
            "architecture_id": "arch_001",
            "architecture_pattern": "microservices",
            "components": [
                {"id": "gw", "type": "api_gateway"},
                {"id": "auth", "type": "service", "replicas": 2, "cpu_limit": 1.0, "memory_limit": 2.0},
                {"id": "order", "type": "service", "replicas": 3, "cpu_limit": 2.0, "memory_limit": 4.0},
                {"id": "db", "type": "database", "technology": "postgresql"},
                {"id": "rd", "type": "cache", "technology": "redis"},
                {"id": "mq", "type": "message_broker", "technology": "kafka"},
            ],
            "dependencies": [
                {"from": "gw", "to": "auth"},
                {"from": "gw", "to": "order"},
                {"from": "order", "to": "db"},
                {"from": "order", "to": "rd"},
                {"from": "order", "to": "mq"},
            ],
        }
        arch = ArchitectureGraph(**graph_data)

        assert arch.node_count == 6
        assert arch.edge_count == 5
        assert arch.service_count == 2
        assert arch.replica_count == 9  # 1 (gw) + 2 (auth) + 3 (order) + 1 (db) + 1 (rd) + 1 (mq)
        assert arch.database == "postgres"  # Cleaned technology
        assert arch.cache == "redis"
        assert arch.messaging == "kafka"
        assert arch.cpu_limit == 12.0  # 1*1 + 2*1 + 3*2 + 1*1 + 1*1 + 1*1 = 12.0

    def test_component_validation_bounds(self):
        """Rejects non-positive replicas or negative CPU limits."""
        with pytest.raises(ValidationError):
            ArchitectureComponent(id="svc", replicas=0)

        with pytest.raises(ValidationError):
            ArchitectureComponent(id="svc", cpu_limit=-1.0)


# =============================================================================
# 2. Graph Extractor & Topological Metrics Tests (Section 9 & Table 9)
# =============================================================================
class TestArchitectureGraphExtractor:
    """Verifies NetworkX graph building and topological feature extraction."""

    def test_extract_from_react_flow_format(self):
        """Converts standard React Flow canvas export (nodes/edges) into NetworkX."""
        react_flow_dict = {
            "architecture_id": "rf_01",
            "architecture_pattern": "modular_monolith",
            "nodes": [
                {"id": "client", "data": {"label": "Web Client", "type": "client"}},
                {"id": "app", "data": {"label": "Monolith Core", "type": "monolith", "replicas": 4}},
                {"id": "db", "data": {"label": "PostgreSQL", "type": "database", "technology": "postgres"}},
            ],
            "edges": [
                {"source": "client", "target": "app"},
                {"source": "app", "target": "db"},
            ],
        }
        G, arch = ArchitectureGraphExtractor.to_networkx(react_flow_dict)

        assert G.number_of_nodes() == 3
        assert G.number_of_edges() == 2
        assert G.has_edge("client", "app")
        assert G.has_edge("app", "db")

    def test_topological_metrics_linear_pipeline(self):
        """Tests linear chain: Client -> Gateway -> Service -> Database."""
        G = nx.DiGraph()
        G.add_edge("client", "gw")
        G.add_edge("gw", "svc")
        G.add_edge("svc", "db")

        metrics = ArchitectureGraphExtractor.extract_topological_features(G)
        assert metrics["graph_depth"] == 3
        assert metrics["max_fan_in"] == 1
        assert metrics["max_fan_out"] == 1
        assert metrics["critical_path_length"] == 4.5  # 3 * 1.5

    def test_topological_metrics_star_topology(self):
        """Tests star topology with high fan-out: Gateway calls 4 independent services."""
        G = nx.DiGraph()
        for i in range(1, 5):
            G.add_edge("gw", f"svc_{i}")

        metrics = ArchitectureGraphExtractor.extract_topological_features(G)
        assert metrics["graph_depth"] == 1
        assert metrics["max_fan_out"] == 4
        assert metrics["max_fan_in"] == 1
        assert metrics["architecture_complexity_score"] > 0

    def test_graph_validation_detects_cycles_and_isolates(self):
        """Detects circular dependencies and isolated components (Table 8)."""
        G = nx.DiGraph()
        G.add_edge("svc_a", "svc_b")
        G.add_edge("svc_b", "svc_a")  # Circular cycle!
        G.add_node("orphan_node")      # Isolated!

        validation = ArchitectureGraphExtractor.validate_graph_structure(G)
        assert validation["is_valid"] is False
        assert validation["is_dag"] is False
        assert len(validation["cycles"]) > 0
        assert "orphan_node" in validation["isolated_nodes"]

    def test_empty_graph_graceful_handling(self):
        """Empty graph returns valid zero-valued metrics without crashing."""
        G = nx.DiGraph()
        metrics = ArchitectureGraphExtractor.extract_topological_features(G)
        assert metrics["graph_depth"] == 0
        assert metrics["average_degree"] == 0.0
        assert metrics["architecture_complexity_score"] == 0.0


# =============================================================================
# 3. ML-Compatible Representation & Encoding Tests (Section 9.1 & 10.1)
# =============================================================================
class TestMLArchitectureRepresentation:
    """Verifies end-to-end vector generation, column alignment, and encoding safety."""

    @pytest.fixture
    def sample_architecture(self):
        return {
            "architecture_id": "arch_ecommerce_sample",
            "architecture_pattern": "microservices",
            "architecture_style": "hexagonal",
            "deployment": "kubernetes",
            "cloud": "aws",
            "components": [
                {"id": "gw", "type": "api_gateway"},
                {"id": "cart", "type": "service", "replicas": 3, "cpu_limit": 2.0, "memory_limit": 4.0},
                {"id": "catalog", "type": "service", "replicas": 4, "cpu_limit": 1.0, "memory_limit": 2.0},
                {"id": "db", "type": "database", "technology": "postgres"},
                {"id": "rd", "type": "cache", "technology": "redis"},
            ],
            "dependencies": [
                {"from": "gw", "to": "cart"},
                {"from": "gw", "to": "catalog"},
                {"from": "cart", "to": "rd"},
                {"from": "cart", "to": "db"},
                {"from": "catalog", "to": "db"},
            ],
        }

    @pytest.fixture
    def sample_requirements(self):
        return NormalizedRequirement(
            domain="ecommerce",
            users=2_000_000,
            rps=4000.0,
            peak_rps=8000.0,
            budget=300000.0,
            availability_sla=99.99,
            data_size=500.0,
            workload_type="transactional",
        )

    def test_build_feature_dataframe_columns(self, sample_architecture, sample_requirements):
        """Verifies DataFrame strictly contains all 31 columns from ALL_FEATURE_COLUMNS."""
        encoder = MLArchitectureRepresentation()
        df = encoder.build_feature_dataframe(sample_architecture, sample_requirements)

        assert df.shape == (1, len(ALL_FEATURE_COLUMNS))
        assert list(df.columns) == ALL_FEATURE_COLUMNS
        assert df["database"].iloc[0] == "postgres"
        assert df["cache"].iloc[0] == "redis"
        assert df["rps"].iloc[0] == 4000.0
        assert df["service_count"].iloc[0] == 2

    def test_encode_feature_vector_shape_and_dtype(self, sample_architecture, sample_requirements):
        """Verifies encoded 1D vector is float32 and matches total feature count."""
        encoder = MLArchitectureRepresentation()
        feat_dict = encoder.build_feature_dict(sample_architecture, sample_requirements)
        vector = encoder.encode_feature_vector(feat_dict)

        assert isinstance(vector, np.ndarray)
        assert vector.dtype == np.float32
        assert len(vector) == len(ALL_FEATURE_COLUMNS)
        assert not np.isnan(vector).any()

    def test_deterministic_reproducibility(self, sample_architecture, sample_requirements):
        """Section 12: Identical architectures produce identical features regardless of origin."""
        encoder = MLArchitectureRepresentation()
        vec1 = encoder.encode_feature_vector(encoder.build_feature_dict(sample_architecture, sample_requirements))
        vec2 = encoder.encode_feature_vector(encoder.build_feature_dict(sample_architecture, sample_requirements))

        np.testing.assert_array_equal(vec1, vec2)

    def test_unseen_category_safety(self, sample_architecture, sample_requirements):
        """Section 12: Novel/unseen categories fallback safely without breaking prediction."""
        encoder = MLArchitectureRepresentation()
        modified_arch = dict(sample_architecture)
        modified_arch["architecture_pattern"] = "serverless_quantum_mesh"  # Unseen!
        modified_arch["database"] = "exotic_graph_db"                    # Unseen!

        feat_dict = encoder.build_feature_dict(modified_arch, sample_requirements)
        vector = encoder.encode_feature_vector(feat_dict)

        assert isinstance(vector, np.ndarray)
        assert len(vector) == len(ALL_FEATURE_COLUMNS)
        assert not np.isnan(vector).any()

    def test_target_leakage_rejection(self, sample_architecture, sample_requirements):
        """Section 9.2: Passing runtime measured targets raises ValueError."""
        encoder = MLArchitectureRepresentation()
        feat_dict = encoder.build_feature_dict(sample_architecture, sample_requirements)
        
        # Inject forbidden runtime target
        feat_dict["latency"] = 45.2

        with pytest.raises(ValueError) as exc_info:
            encoder._validate_leakage_absence(feat_dict)
        assert "Target Leakage detected" in str(exc_info.value)
