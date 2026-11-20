import type { Architecture } from '../../types'
import type { ArchEdge, ArchNode, BuilderConfig } from './model'

export interface ExportedGraph {
  nodes: { id: string; type: string; name: string; tech?: string }[]
  edges: { source: string; target: string; communication: string }[]
}

export interface BuildResult {
  architecture: Architecture
  graph: ExportedGraph
  warnings: string[]
}

export function slugify(name: string): string {
  return name.toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '')
}

// Turns the drawn graph plus the settings into the payload shape of
// architecture.schema.json. This is the "architecture diagram -> machine-readable
// features" step from README section 14: counts and technologies are DERIVED from
// the graph, not typed in twice.
export function buildArchitecture(nodes: ArchNode[], edges: ArchEdge[], config: BuilderConfig): BuildResult {
  const warnings: string[] = []

  const techOf = (kind: 'database' | 'cache' | 'message_broker', fallback: string): string => {
    const found = nodes.filter((n) => n.data.kind === kind)
    if (found.length > 1) {
      warnings.push(`${found.length} ${kind} nodes found; the schema holds one, so the first is used.`)
    }
    return found[0] ? (found[0].data.tech ?? fallback) : 'none'
  }

  const architecture = {
    architecture_id: slugify(config.name),
    architecture_pattern: config.architecture_pattern,
    architecture_style: config.architecture_style,
    service_count: nodes.filter((n) => n.data.kind === 'service').length,
    database: techOf('database', 'postgres'),
    cache: techOf('cache', 'redis'),
    messaging: techOf('message_broker', 'kafka'),
    api_style: config.api_style,
    deployment: config.deployment,
    cloud: config.cloud,
    replica_count: config.replica_count,
    cpu_limit: config.cpu_limit,
    memory_limit: config.memory_limit,
    node_count: nodes.length,
    edge_count: edges.length,
  } as Architecture

  const graph: ExportedGraph = {
    nodes: nodes.map((n) => ({ id: n.id, type: n.data.kind, name: n.data.label, ...(n.data.tech ? { tech: n.data.tech } : {}) })),
    edges: edges.map((e) => ({ source: e.source, target: e.target, communication: e.data?.communication ?? 'HTTP' })),
  }

  return { architecture, graph, warnings }
}
