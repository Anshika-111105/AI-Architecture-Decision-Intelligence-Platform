import { z } from 'zod'

// Runtime validation mirroring packages/shared-schemas/architecture.schema.json.
// If that JSON schema changes, update this file too (the generated TypeScript
// types in src/types/generated/ are only compile-time checks).
const num = () => z.number({ error: 'Enter a number' })

export const architectureSchema = z.object({
  architecture_id: z.string().min(1, 'Give the architecture a name'),
  architecture_pattern: z.enum(['monolith', 'modular_monolith', 'microservices', 'event_driven', 'serverless']),
  architecture_style: z.enum(['layered', 'hexagonal', 'cqrs', 'event_sourcing', 'pipeline', 'service_oriented']).optional(),
  service_count: num().int().min(1, 'Add at least one Service node').max(200),
  database: z.enum(['postgres', 'mysql', 'mongodb', 'dynamodb', 'cassandra', 'redis_only', 'none']),
  cache: z.enum(['none', 'redis', 'memcached', 'hazelcast']),
  messaging: z.enum(['none', 'kafka', 'rabbitmq', 'aws_sqs', 'nats']),
  api_style: z.enum(['rest', 'graphql', 'grpc', 'websocket']),
  deployment: z.enum(['docker_compose', 'kubernetes', 'aws_ecs', 'aws_lambda', 'bare_metal_vm']),
  cloud: z.enum(['aws', 'gcp', 'azure', 'on_premise']).optional(),
  replica_count: num().int().min(1).max(128),
  cpu_limit: num().min(0.25, 'At least 0.25 vCPU').optional(),
  memory_limit: num().min(0.5, 'At least 0.5 GB').optional(),
  node_count: num().int().min(1, 'The graph needs at least one node'),
  edge_count: num().int().min(0),
})
