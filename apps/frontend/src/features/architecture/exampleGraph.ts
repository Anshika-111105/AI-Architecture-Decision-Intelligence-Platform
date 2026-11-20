import { MarkerType } from '@xyflow/react'
import type { ArchEdge, ArchNode, NodeKind } from './model'

const node = (id: string, kind: NodeKind, label: string, x: number, y: number, tech?: string): ArchNode => ({
  id,
  type: 'arch',
  position: { x, y },
  data: { kind, label, ...(tech ? { tech } : {}) },
})

const edge = (source: string, target: string, communication: string): ArchEdge => ({
  id: `${source}->${target}`,
  source,
  target,
  label: communication,
  data: { communication },
  markerEnd: { type: MarkerType.ArrowClosed },
})

// The example from README section 14.
export const EXAMPLE_NODES: ArchNode[] = [
  node('frontend', 'client', 'Frontend', 0, 160),
  node('gateway', 'api_gateway', 'API Gateway', 220, 160),
  node('order_service', 'service', 'Order Service', 440, 160),
  node('redis', 'cache', 'Redis', 700, 40, 'redis'),
  node('postgres', 'database', 'PostgreSQL', 700, 160, 'postgres'),
  node('kafka', 'message_broker', 'Kafka', 700, 280, 'kafka'),
]

export const EXAMPLE_EDGES: ArchEdge[] = [
  edge('frontend', 'gateway', 'HTTP'),
  edge('gateway', 'order_service', 'HTTP'),
  edge('order_service', 'redis', 'TCP'),
  edge('order_service', 'postgres', 'TCP'),
  edge('order_service', 'kafka', 'async'),
]
