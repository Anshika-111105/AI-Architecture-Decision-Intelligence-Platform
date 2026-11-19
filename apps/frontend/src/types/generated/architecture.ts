/* AUTO-GENERATED from packages/shared-schemas/architecture.schema.json. DO NOT EDIT. */

/**
 * Dataset B: Formal schema for candidate architecture configurations and graph topologies
 */
export interface ADIP_Architecture_Schema {
  /**
   * Unique identifier for candidate architecture
   */
  architecture_id: string;
  architecture_pattern: "monolith" | "modular_monolith" | "microservices" | "event_driven" | "serverless";
  architecture_style?: "layered" | "hexagonal" | "cqrs" | "event_sourcing" | "pipeline" | "service_oriented";
  service_count: number;
  database: "postgres" | "mysql" | "mongodb" | "dynamodb" | "cassandra" | "redis_only" | "none";
  cache: "none" | "redis" | "memcached" | "hazelcast";
  messaging: "none" | "kafka" | "rabbitmq" | "aws_sqs" | "nats";
  api_style: "rest" | "graphql" | "grpc" | "websocket";
  deployment: "docker_compose" | "kubernetes" | "aws_ecs" | "aws_lambda" | "bare_metal_vm";
  cloud?: "aws" | "gcp" | "azure" | "on_premise";
  replica_count: number;
  /**
   * Allocated vCPU
   */
  cpu_limit?: number;
  /**
   * Allocated memory in GB
   */
  memory_limit?: number;
  /**
   * Total nodes in architecture dependency graph
   */
  node_count: number;
  /**
   * Total directed edges in architecture dependency graph
   */
  edge_count: number;
}
