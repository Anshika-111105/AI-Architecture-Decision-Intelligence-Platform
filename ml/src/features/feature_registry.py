from typing import List, Dict, Any

# Categorical domain definitions
CATEGORICAL_FEATURES = {
    "architecture_pattern": ["monolith", "modular_monolith", "microservices", "event_driven", "serverless"],
    "architecture_style": ["layered", "hexagonal", "cqrs", "event_sourcing", "pipeline", "service_oriented"],
    "database": ["postgres", "mysql", "mongodb", "dynamodb", "cassandra", "redis_only", "none"],
    "cache": ["none", "redis", "memcached", "hazelcast"],
    "messaging": ["none", "kafka", "rabbitmq", "aws_sqs", "nats"],
    "api_style": ["rest", "graphql", "grpc", "websocket"],
    "deployment": ["docker_compose", "kubernetes", "aws_ecs", "aws_lambda", "bare_metal_vm"],
    "cloud": ["aws", "gcp", "azure", "on_premise"],
    "workload_type": ["oltp", "olap", "read_heavy", "write_heavy", "balanced", "streaming"],
    "traffic_pattern": ["steady", "bursty", "diurnal", "exponential_spike", "gradual_ramp"],
}

# Numerical feature lists
BASE_NUMERICAL_FEATURES = [
    # Architecture dimensions
    "service_count",
    "replica_count",
    "cpu_limit",
    "memory_limit",
    "node_count",
    "edge_count",
    # Workload dimensions
    "rps",
    "concurrency",
    "read_write_ratio",
    "data_size",
    "request_size",
]

GRAPH_TOPOLOGY_FEATURES = [
    "graph_depth",
    "average_degree",
    "max_fan_in",
    "max_fan_out",
    "critical_path_length",
    "architecture_complexity_score",
]

INTERACTION_FEATURES = [
    "rps_per_service",
    "concurrency_per_replica",
    "data_per_request_ratio",
    "cache_capacity_coverage",
]

ALL_FEATURE_COLUMNS = (
    list(CATEGORICAL_FEATURES.keys())
    + BASE_NUMERICAL_FEATURES
    + GRAPH_TOPOLOGY_FEATURES
    + INTERACTION_FEATURES
)

# Target definitions per model
MODEL_TARGETS: Dict[str, List[str]] = {
    "latency": ["p50", "p95", "p99"],
    "throughput": ["throughput"],
    "resources": ["cpu", "memory"],
    "cost": ["monthly_cost"],
    "reliability": ["error_rate"],
}


def get_feature_schema() -> Dict[str, Any]:
    """Returns structured dictionary of feature registry for validation."""
    return {
        "categoricals": CATEGORICAL_FEATURES,
        "base_numerical": BASE_NUMERICAL_FEATURES,
        "graph_topology": GRAPH_TOPOLOGY_FEATURES,
        "interactions": INTERACTION_FEATURES,
        "targets": MODEL_TARGETS,
        "total_feature_count": len(ALL_FEATURE_COLUMNS),
    }
