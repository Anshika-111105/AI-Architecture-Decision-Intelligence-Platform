import logging
from typing import Dict, Any, Optional, List, Tuple, Union
import numpy as np
import networkx as nx

from ml.src.architecture.schemas import (
    ArchitectureGraph,
    ArchitectureComponent,
    ArchitectureDependency,
)

logger = logging.getLogger("ADIP_ArchitectureGraphExtractor")


class ArchitectureGraphExtractor:
    """
    Transforms candidate architecture diagrams (React Flow JSON, PostgreSQL schema,
    or ArchitectureGraph models) into NetworkX DiGraphs and extracts structural
    and topological metrics.
    """

    def __init__(self):
        logger.info("ArchitectureGraphExtractor initialized.")

    @classmethod
    def to_networkx(
        cls,
        architecture: Union[ArchitectureGraph, Dict[str, Any]]
    ) -> Tuple[nx.DiGraph, ArchitectureGraph]:
        """
        Converts ArchitectureGraph or raw dict (including React Flow format)
        into a NetworkX directed graph (DiGraph) and a validated ArchitectureGraph model.
        """
        if isinstance(architecture, ArchitectureGraph):
            arch_model = architecture
        elif isinstance(architecture, dict):
            # Check for React Flow format: {"nodes": [...], "edges": [...]}
            if "nodes" in architecture and "components" not in architecture:
                normalized_dict = cls._from_react_flow_dict(architecture)
                arch_model = ArchitectureGraph(**normalized_dict)
            else:
                arch_model = ArchitectureGraph(**architecture)
        else:
            raise TypeError(f"Unsupported architecture type: {type(architecture)}")

        G = nx.DiGraph()
        G.graph["architecture_id"] = arch_model.architecture_id
        G.graph["pattern"] = arch_model.architecture_pattern
        G.graph["style"] = arch_model.architecture_style

        # Add Nodes with component attributes
        for comp in arch_model.components:
            G.add_node(
                comp.id,
                name=comp.name or comp.id,
                type=comp.type,
                category=comp.category,
                technology=comp.technology,
                replicas=comp.replicas,
                cpu_limit=comp.cpu_limit,
                memory_limit=comp.memory_limit,
            )

        # Add Directed Edges with protocol attributes
        for dep in arch_model.dependencies:
            G.add_edge(
                dep.source,
                dep.target,
                protocol=dep.protocol or "rest",
                sync=dep.sync,
                bandwidth_mbps=dep.bandwidth_mbps,
            )

        return G, arch_model

    @staticmethod
    def _from_react_flow_dict(raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adapts standard React Flow canvas export (nodes and edges)
        into ADIP ArchitectureGraph schema dictionary.
        """
        components = []
        for node in raw.get("nodes", []):
            node_id = str(node.get("id"))
            data = node.get("data", {})
            components.append({
                "id": node_id,
                "name": data.get("label", node_id),
                "type": data.get("type", node.get("type", "service")),
                "technology": data.get("technology"),
                "replicas": data.get("replicas", 1),
                "cpu_limit": data.get("cpu_limit", 1.0),
                "memory_limit": data.get("memory_limit", 2.0),
            })

        dependencies = []
        for edge in raw.get("edges", []):
            dependencies.append({
                "source": str(edge.get("source")),
                "target": str(edge.get("target")),
                "protocol": edge.get("data", {}).get("protocol", "rest"),
                "sync": edge.get("data", {}).get("sync", True),
            })

        return {
            "architecture_id": raw.get("architecture_id", "react_flow_arch"),
            "project_id": raw.get("project_id"),
            "architecture_pattern": raw.get("architecture_pattern", "microservices"),
            "architecture_style": raw.get("architecture_style", "hexagonal"),
            "api_style": raw.get("api_style", "rest"),
            "deployment": raw.get("deployment", "kubernetes"),
            "cloud": raw.get("cloud", "aws"),
            "components": components,
            "dependencies": dependencies,
        }

    @classmethod
    def extract_topological_features(cls, G: nx.DiGraph) -> Dict[str, float]:
        """
        Extracts structural NetworkX metrics:
          - graph_depth: Longest dependency path in DAG
          - average_degree: Mean connections per node
          - max_fan_in: Maximum incoming call concentration
          - max_fan_out: Maximum outbound call distribution
          - critical_path_length: Estimated execution pipeline depth
          - graph_density: Edge saturation ratio
          - architecture_complexity_score: Combined node/edge/fan-out metric
          - coupling_metric: Ratio of total dependencies to service nodes
        """
        node_count = G.number_of_nodes()
        edge_count = G.number_of_edges()

        if node_count == 0:
            return {
                "graph_depth": 0,
                "average_degree": 0.0,
                "max_fan_in": 0,
                "max_fan_out": 0,
                "critical_path_length": 0.0,
                "graph_density": 0.0,
                "architecture_complexity_score": 0.0,
                "coupling_metric": 0.0,
            }

        in_degrees = [d for _, d in G.in_degree()]
        out_degrees = [d for _, d in G.out_degree()]

        max_fan_in = max(in_degrees) if in_degrees else 0
        max_fan_out = max(out_degrees) if out_degrees else 0
        avg_degree = round(float(edge_count) / float(node_count), 3)

        # Graph density
        if node_count > 1:
            density = round(edge_count / float(node_count * (node_count - 1)), 4)
        else:
            density = 0.0

        # Graph depth (longest path in DAG; fallback to condensation if cyclic)
        try:
            if nx.is_directed_acyclic_graph(G):
                graph_depth = nx.dag_longest_path_length(G)
            else:
                condensation = nx.condensation(G)
                graph_depth = nx.dag_longest_path_length(condensation)
        except Exception:
            graph_depth = int(np.log2(node_count + 1))

        # Critical path length (path depth * 1.5 multiplier)
        critical_path_length = round(float(graph_depth) * 1.5, 2)

        # Architecture complexity score (structural weight combining size and fan-out)
        complexity = round(
            (node_count * 0.4) + (edge_count * 0.6) * (1.0 + (max_fan_out / 5.0)),
            3
        )

        # Coupling metric (interdependency ratio)
        coupling = round(float(edge_count) / float(max(node_count, 1)), 3)

        return {
            "graph_depth": int(graph_depth),
            "average_degree": avg_degree,
            "max_fan_in": int(max_fan_in),
            "max_fan_out": int(max_fan_out),
            "critical_path_length": critical_path_length,
            "graph_density": density,
            "architecture_complexity_score": complexity,
            "coupling_metric": coupling,
        }

    @classmethod
    def validate_graph_structure(cls, G: nx.DiGraph) -> Dict[str, Any]:
        """
        Validates graph integrity for visual feedback and rule validation (Table 8):
          - Cycles detection (circular dependencies between services)
          - Isolated components (orphaned nodes with no edges)
          - Entry points (nodes with in-degree = 0)
          - Sink nodes (nodes with out-degree = 0, e.g. databases, queues)
        """
        node_count = G.number_of_nodes()
        if node_count == 0:
            return {
                "is_valid": False,
                "errors": ["Architecture graph has no components."],
                "is_dag": True,
                "cycles": [],
                "isolated_nodes": [],
            }

        errors = []
        is_dag = nx.is_directed_acyclic_graph(G)
        cycles = list(nx.simple_cycles(G)) if not is_dag else []

        # Find isolated nodes
        isolated_nodes = list(nx.isolates(G))
        if isolated_nodes:
            errors.append(f"Isolated components detected (no connections): {isolated_nodes}")

        # Find entry points (in-degree == 0)
        entry_points = [n for n, d in G.in_degree() if d == 0 and n not in isolated_nodes]
        if not entry_points and node_count > 1:
            errors.append("No entry point detected (every node has incoming dependencies).")

        # Find sinks (out-degree == 0)
        sinks = [n for n, d in G.out_degree() if d == 0 and n not in isolated_nodes]

        is_valid = len(errors) == 0

        return {
            "is_valid": is_valid,
            "errors": errors,
            "is_dag": is_dag,
            "cycles": cycles,
            "isolated_nodes": isolated_nodes,
            "entry_points": entry_points,
            "sinks": sinks,
            "node_count": node_count,
            "edge_count": G.number_of_edges(),
        }

    @classmethod
    def extract_features(
        cls,
        architecture: Union[ArchitectureGraph, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Extracts all static and topological architecture features ready for representation:
          - Pattern & style categoricals
          - Size & capacity dimensions
          - NetworkX graph metrics
        """
        G, arch_model = cls.to_networkx(architecture)
        graph_metrics = cls.extract_topological_features(G)

        features: Dict[str, Any] = {
            # Categorical dimensions
            "architecture_pattern": arch_model.architecture_pattern,
            "architecture_style": arch_model.architecture_style,
            "database": arch_model.database,
            "cache": arch_model.cache,
            "messaging": arch_model.messaging,
            "api_style": arch_model.api_style,
            "deployment": arch_model.deployment,
            "cloud": arch_model.cloud,
            # Numerical size & capacity dimensions
            "service_count": arch_model.service_count,
            "replica_count": arch_model.replica_count,
            "cpu_limit": arch_model.cpu_limit,
            "memory_limit": arch_model.memory_limit,
            "node_count": arch_model.node_count,
            "edge_count": arch_model.edge_count,
        }

        # Merge graph metrics
        features.update(graph_metrics)
        return features
