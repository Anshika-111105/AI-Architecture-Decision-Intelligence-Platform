import type { Edge, Node } from '@xyflow/react'

// The six component kinds from README section 14 (architecture graph representation).
export const NODE_KINDS = ['client', 'api_gateway', 'service', 'cache', 'database', 'message_broker'] as const
export type NodeKind = (typeof NODE_KINDS)[number]

export const KIND_LABELS: Record<NodeKind, string> = {
  client: 'Client',
  api_gateway: 'API Gateway',
  service: 'Service',
  cache: 'Cache',
  database: 'Database',
  message_broker: 'Message Broker',
}

// Technology choices come straight from the enums in architecture.schema.json.
export const TECH_OPTIONS: Partial<Record<NodeKind, readonly string[]>> = {
  database: ['postgres', 'mysql', 'mongodb', 'dynamodb', 'cassandra', 'redis_only'],
  cache: ['redis', 'memcached', 'hazelcast'],
  message_broker: ['kafka', 'rabbitmq', 'aws_sqs', 'nats'],
}

export const DEFAULT_TECH: Partial<Record<NodeKind, string>> = {
  database: 'postgres',
  cache: 'redis',
  message_broker: 'kafka',
}

export const COMMUNICATIONS = ['HTTP', 'gRPC', 'TCP', 'async', 'WebSocket'] as const

export type ArchNodeData = { kind: NodeKind; label: string; tech?: string }
export type ArchNode = Node<ArchNodeData, 'arch'>
export type ArchEdgeData = { communication: string }
export type ArchEdge = Edge<ArchEdgeData>

// Architecture-level settings the user picks (everything the graph cannot tell us).
export interface BuilderConfig {
  name: string
  architecture_pattern: string
  architecture_style: string
  api_style: string
  deployment: string
  cloud: string
  replica_count: number
  cpu_limit: number
  memory_limit: number
}

export const DEFAULT_CONFIG: BuilderConfig = {
  name: '',
  architecture_pattern: 'microservices',
  architecture_style: 'layered',
  api_style: 'rest',
  deployment: 'kubernetes',
  cloud: 'aws',
  replica_count: 3,
  cpu_limit: 2,
  memory_limit: 4,
}

export const ENUMS = {
  architecture_pattern: ['monolith', 'modular_monolith', 'microservices', 'event_driven', 'serverless'],
  architecture_style: ['layered', 'hexagonal', 'cqrs', 'event_sourcing', 'pipeline', 'service_oriented'],
  api_style: ['rest', 'graphql', 'grpc', 'websocket'],
  deployment: ['docker_compose', 'kubernetes', 'aws_ecs', 'aws_lambda', 'bare_metal_vm'],
  cloud: ['aws', 'gcp', 'azure', 'on_premise'],
} as const
