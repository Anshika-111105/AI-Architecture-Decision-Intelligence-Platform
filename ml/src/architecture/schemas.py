from enum import Enum
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, model_validator, ConfigDict


# =============================================================================
# Controlled Vocabulary Enums (Aligned with Phase 4 feature_registry.py)
# =============================================================================

class ArchitecturePattern(str, Enum):
    MONOLITH = "monolith"
    MODULAR_MONOLITH = "modular_monolith"
    MICROSERVICES = "microservices"
    EVENT_DRIVEN = "event_driven"
    SERVERLESS = "serverless"


class ArchitectureStyle(str, Enum):
    LAYERED = "layered"
    HEXAGONAL = "hexagonal"
    CQRS = "cqrs"
    EVENT_SOURCING = "event_sourcing"
    PIPELINE = "pipeline"
    SERVICE_ORIENTED = "service_oriented"


class ApiStyle(str, Enum):
    REST = "rest"
    GRAPHQL = "graphql"
    GRPC = "grpc"
    WEBSOCKET = "websocket"


class DeploymentType(str, Enum):
    DOCKER_COMPOSE = "docker_compose"
    KUBERNETES = "kubernetes"
    AWS_ECS = "aws_ecs"
    AWS_LAMBDA = "aws_lambda"
    BARE_METAL_VM = "bare_metal_vm"


class CloudProvider(str, Enum):
    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"
    ON_PREMISE = "on_premise"


class ComponentCategory(str, Enum):
    """Component category grouping defined in Phase 6 Table 7."""
    ENTRY = "entry"            # client, load balancer, api gateway
    APPLICATION = "application"# service, monolith, module, worker
    DATA = "data"              # relational/document db, storage
    PERFORMANCE = "performance"# cache (redis, memcached)
    COMMUNICATION = "communication" # broker (kafka, rabbitmq, sqs)
    DEPLOYMENT = "deployment"  # container, pod, vm


class ComponentType(str, Enum):
    API_GATEWAY = "api_gateway"
    LOAD_BALANCER = "load_balancer"
    CLIENT = "client"
    SERVICE = "service"
    MONOLITH = "monolith"
    DATABASE = "database"
    CACHE = "cache"
    MESSAGE_BROKER = "message_broker"
    QUEUE = "queue"
    WORKER = "worker"
    STORAGE = "storage"
    OTHER = "other"


# =============================================================================
# Graph Component (Node) & Dependency (Edge) Models
# =============================================================================

class ArchitectureComponent(BaseModel):
    """
    Represents an individual node in the architecture graph (React Flow canvas).
    """
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(description="Unique component identifier (e.g., 'gw', 'auth_service', 'db')")
    name: Optional[str] = Field(default=None, description="Human-readable component label")
    type: str = Field(default="service", description="Component type: gateway, service, database, cache, broker")
    category: Optional[str] = Field(default=None, description="Broad category: entry, application, data, performance, communication")
    technology: Optional[str] = Field(default=None, description="Specific technology: postgresql, redis, kafka, etc.")
    replicas: int = Field(default=1, ge=1, description="Number of running replicas or instances (must be >= 1)")
    cpu_limit: float = Field(default=1.0, ge=0.1, description="Allocated CPU cores per replica (must be >= 0.1)")
    memory_limit: float = Field(default=2.0, ge=0.1, description="Allocated Memory in GB per replica (must be >= 0.1)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional custom attributes or React Flow UI coordinates")

    @model_validator(mode="after")
    def infer_category_and_type(self) -> "ArchitectureComponent":
        """Infers category from type if category is not explicitly provided."""
        t = self.type.lower()
        if not self.category:
            if t in ["api_gateway", "load_balancer", "client", "ingress"]:
                self.category = ComponentCategory.ENTRY.value
            elif t in ["database", "db", "datastore", "sql", "nosql"]:
                self.category = ComponentCategory.DATA.value
            elif t in ["cache", "redis", "memcached"]:
                self.category = ComponentCategory.PERFORMANCE.value
            elif t in ["message_broker", "broker", "queue", "kafka", "rabbitmq"]:
                self.category = ComponentCategory.COMMUNICATION.value
            else:
                self.category = ComponentCategory.APPLICATION.value
        return self


class ArchitectureDependency(BaseModel):
    """
    Represents a directed communication edge between components in the architecture.
    Supports both React Flow ('source', 'target') and schema ('from', 'to') formats.
    """
    model_config = ConfigDict(populate_by_name=True)

    source: str = Field(alias="from", description="Originating component ID")
    target: str = Field(alias="to", description="Target component ID")
    protocol: Optional[str] = Field(default="rest", description="Communication protocol: rest, grpc, async, sql, redis")
    sync: bool = Field(default=True, description="Whether interaction is synchronous (blocking) or asynchronous")
    bandwidth_mbps: Optional[float] = Field(default=None, ge=0.0, description="Estimated network transfer rate in Mbps")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="React Flow edge options or routing weights")

    @model_validator(mode="before")
    @classmethod
    def normalize_source_target(cls, data: Any) -> Any:
        """Allows either ('from', 'to') or ('source', 'target') keys."""
        if isinstance(data, dict):
            if "from" in data and "source" not in data:
                data["source"] = data["from"]
            if "to" in data and "target" not in data:
                data["target"] = data["to"]
        return data


# =============================================================================
# Complete Architecture Graph Schema
# =============================================================================

class ArchitectureGraph(BaseModel):
    """
    Full architecture schema aligned with Dataset B — Architecture (Phase 3/4)
    and React Flow visual builder payloads (Section 5).
    """
    model_config = ConfigDict(populate_by_name=True)

    architecture_id: str = Field(description="Unique architecture identifier")
    project_id: Optional[str] = Field(default=None, description="Linked project identifier")
    name: Optional[str] = Field(default=None, description="Descriptive architecture name")
    architecture_pattern: str = Field(default="microservices", description="Pattern: monolith, microservices, serverless, etc.")
    architecture_style: str = Field(default="hexagonal", description="Style: layered, hexagonal, cqrs, event_sourcing")
    api_style: str = Field(default="rest", description="API style: rest, graphql, grpc")
    deployment: str = Field(default="kubernetes", description="Deployment: docker_compose, kubernetes, aws_ecs")
    cloud: str = Field(default="aws", description="Target cloud: aws, gcp, azure, on_premise")

    # Nodes & Edges
    components: List[ArchitectureComponent] = Field(default_factory=list, description="List of architecture nodes/components")
    dependencies: List[ArchitectureDependency] = Field(default_factory=list, description="List of directed dependencies/edges")

    # Explicit / Overridable dimensions (Derived automatically if omitted)
    database: Optional[str] = Field(default=None, description="Primary database technology")
    cache: Optional[str] = Field(default=None, description="Primary cache technology")
    messaging: Optional[str] = Field(default=None, description="Primary messaging technology")
    service_count: Optional[int] = Field(default=None, ge=1, description="Number of application services (derived if omitted)")
    node_count: Optional[int] = Field(default=None, ge=1, description="Total node count (derived if omitted)")
    edge_count: Optional[int] = Field(default=None, ge=0, description="Total edge count (derived if omitted)")
    replica_count: Optional[int] = Field(default=None, ge=1, description="Total replica count across services")
    cpu_limit: Optional[float] = Field(default=None, ge=0.1, description="Aggregated CPU limit")
    memory_limit: Optional[float] = Field(default=None, ge=0.1, description="Aggregated Memory limit in GB")

    @model_validator(mode="after")
    def derive_counts_and_technologies(self) -> "ArchitectureGraph":
        """
        Derives structural counts and technologies directly from components and dependencies
        to guarantee consistency with the diagram (Section 5: Derived counts always match).
        """
        # Node & Edge counts
        actual_node_count = len(self.components)
        actual_edge_count = len(self.dependencies)

        if actual_node_count > 0:
            self.node_count = actual_node_count
            self.edge_count = actual_edge_count

            # Count application services
            app_services = [
                c for c in self.components
                if c.category == ComponentCategory.APPLICATION.value or c.type in ["service", "monolith", "worker"]
            ]
            self.service_count = max(len(app_services), 1)

            # Sum replicas, cpu, memory
            self.replica_count = sum(c.replicas for c in self.components)
            self.cpu_limit = round(sum(c.cpu_limit * c.replicas for c in self.components), 2)
            self.memory_limit = round(sum(c.memory_limit * c.replicas for c in self.components), 2)

            # Discover database technology
            if not self.database:
                db_nodes = [c for c in self.components if c.type in ["database", "db"] or c.category == ComponentCategory.DATA.value]
                if db_nodes:
                    tech = db_nodes[0].technology or db_nodes[0].name or "postgres"
                    self.database = self._clean_tech_name(tech)
                else:
                    self.database = "none"

            # Discover cache technology
            if not self.cache:
                cache_nodes = [c for c in self.components if c.type in ["cache", "redis"] or c.category == ComponentCategory.PERFORMANCE.value]
                if cache_nodes:
                    tech = cache_nodes[0].technology or cache_nodes[0].name or "redis"
                    self.cache = self._clean_tech_name(tech)
                else:
                    self.cache = "none"

            # Discover messaging technology
            if not self.messaging:
                msg_nodes = [c for c in self.components if c.type in ["message_broker", "queue", "kafka"] or c.category == ComponentCategory.COMMUNICATION.value]
                if msg_nodes:
                    tech = msg_nodes[0].technology or msg_nodes[0].name or "kafka"
                    self.messaging = self._clean_tech_name(tech)
                else:
                    self.messaging = "none"

        return self

    @staticmethod
    def _clean_tech_name(tech: str) -> str:
        """Standardizes technology names to canonical values in feature registry."""
        s = tech.strip().lower()
        if "postgre" in s:
            return "postgres"
        elif "mongo" in s:
            return "mongodb"
        elif "mysql" in s:
            return "mysql"
        elif "dynamo" in s:
            return "dynamodb"
        elif "cassandra" in s:
            return "cassandra"
        elif "redis" in s:
            return "redis"
        elif "kafka" in s:
            return "kafka"
        elif "rabbit" in s:
            return "rabbitmq"
        elif "sqs" in s:
            return "aws_sqs"
        elif "nats" in s:
            return "nats"
        elif "memcached" in s:
            return "memcached"
        return s
