import logging
from typing import Dict, Any, Optional
import numpy as np
import pandas as pd
import networkx as nx

from ml.src.features.feature_registry import (
    CATEGORICAL_FEATURES,
    BASE_NUMERICAL_FEATURES,
    GRAPH_TOPOLOGY_FEATURES,
    INTERACTION_FEATURES,
    ALL_FEATURE_COLUMNS,
    MODEL_TARGETS,
)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [Anshika-FeatureEngineering] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("ADIP_BuildFeatures")


class ArchitectureFeatureBuilder:
    """
    Transforms raw and normalized architecture tables into engineered
    ML feature matrices with graph topology and intensity features.
    """

    def __init__(self):
        logger.info("Initialized ArchitectureFeatureBuilder.")

    def compute_graph_metrics_from_networkx(self, G: nx.DiGraph) -> Dict[str, float]:
        """
        Extracts structural graph metrics from a NetworkX directed graph representation.
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
                "architecture_complexity_score": 0.0,
            }

        in_degrees = [d for _, d in G.in_degree()]
        out_degrees = [d for _, d in G.out_degree()]
        max_fan_in = max(in_degrees) if in_degrees else 0
        max_fan_out = max(out_degrees) if out_degrees else 0
        avg_degree = float(edge_count) / float(node_count)

        # Graph depth (longest path if DAG)
        try:
            if nx.is_directed_acyclic_graph(G):
                graph_depth = nx.dag_longest_path_length(G)
            else:
                graph_depth = int(np.log2(node_count + 1))
        except Exception:
            graph_depth = int(np.log2(node_count + 1))

        # Architecture complexity score
        complexity = (node_count * 0.4) + (edge_count * 0.6) * (1.0 + (max_fan_out / 5.0))

        return {
            "graph_depth": int(graph_depth),
            "average_degree": round(avg_degree, 3),
            "max_fan_in": int(max_fan_in),
            "max_fan_out": int(max_fan_out),
            "critical_path_length": float(graph_depth * 1.5),
            "architecture_complexity_score": round(complexity, 3),
        }

    def compute_interaction_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Computes workload-to-architecture intensity and capacity ratios.
        """
        res = df.copy()

        # Safe defaults
        service_cnt = res["service_count"].clip(lower=1) if "service_count" in res else 1
        replica_cnt = res["replica_count"].clip(lower=1) if "replica_count" in res else 1
        rps_val = res["rps"].clip(lower=1.0) if "rps" in res else 1.0
        data_gb = res["data_size"].clip(lower=0.1) if "data_size" in res else 1.0

        res["rps_per_service"] = rps_val / service_cnt
        res["concurrency_per_replica"] = (res.get("concurrency", 100)) / replica_cnt
        res["data_per_request_ratio"] = (data_gb * 1024.0) / rps_val
        res["cache_capacity_coverage"] = res["cache"].apply(lambda c: 0.0 if str(c).lower() == "none" else 1.0)

        # Estimate graph topology features if not already extracted from graph
        if "graph_depth" not in res.columns:
            res["graph_depth"] = np.ceil(np.log2(service_cnt + 2)).astype(int)
            res["average_degree"] = (res.get("edge_count", service_cnt * 2) / res.get("node_count", service_cnt + 2)).round(2)
            res["max_fan_in"] = service_cnt.clip(upper=10)
            res["max_fan_out"] = service_cnt.clip(upper=10)
            res["critical_path_length"] = res["graph_depth"] * 1.5
            res["architecture_complexity_score"] = (
                res.get("node_count", 5) * 0.4 + res.get("edge_count", 6) * 0.6
            )

        return res

    def build_feature_matrix(self, arch_df: pd.DataFrame, workload_df: pd.DataFrame) -> pd.DataFrame:
        """
        Merges Dataset B (Architecture) and Dataset C (Workload), then engineers features.
        """
        merged = pd.merge(arch_df, workload_df, on="workload_id" if "workload_id" in arch_df and "workload_id" in workload_df else None, how="inner")
        feature_df = self.compute_interaction_features(merged)
        return feature_df


if __name__ == "__main__":
    builder = ArchitectureFeatureBuilder()
    # Test with a mock microservices graph
    G = nx.DiGraph()
    G.add_edge("gateway", "order_service")
    G.add_edge("gateway", "user_service")
    G.add_edge("order_service", "payment_service")
    G.add_edge("order_service", "postgres")
    G.add_edge("order_service", "redis")

    metrics = builder.compute_graph_metrics_from_networkx(G)
    logger.info(f"Graph feature extraction self-test output: {metrics}")
