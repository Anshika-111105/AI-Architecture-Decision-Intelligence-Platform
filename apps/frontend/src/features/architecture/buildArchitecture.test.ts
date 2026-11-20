import { describe, expect, it } from 'vitest'
import { architectureSchema } from '../../types/architecture.zod'
import { buildArchitecture, slugify } from './buildArchitecture'
import { EXAMPLE_EDGES, EXAMPLE_NODES } from './exampleGraph'
import { DEFAULT_CONFIG } from './model'

const config = { ...DEFAULT_CONFIG, name: 'Shop v1' }

describe('buildArchitecture', () => {
  it('derives counts and technologies from the README example graph', () => {
    const { architecture, graph, warnings } = buildArchitecture(EXAMPLE_NODES, EXAMPLE_EDGES, config)
    expect(architecture).toMatchObject({
      architecture_id: 'shop-v1',
      service_count: 1,
      database: 'postgres',
      cache: 'redis',
      messaging: 'kafka',
      node_count: 6,
      edge_count: 5,
    })
    expect(graph.edges).toContainEqual({ source: 'order_service', target: 'kafka', communication: 'async' })
    expect(warnings).toEqual([])
    expect(architectureSchema.safeParse(architecture).success).toBe(true)
  })

  it('uses "none" when the graph has no cache or broker', () => {
    const nodes = EXAMPLE_NODES.filter((n) => n.data.kind !== 'cache' && n.data.kind !== 'message_broker')
    const edges = EXAMPLE_EDGES.filter((e) => e.target !== 'redis' && e.target !== 'kafka')
    const { architecture } = buildArchitecture(nodes, edges, config)
    expect(architecture.cache).toBe('none')
    expect(architecture.messaging).toBe('none')
  })

  it('warns when there is more than one database node', () => {
    const extra = { ...EXAMPLE_NODES[4], id: 'mongo', data: { kind: 'database' as const, label: 'Mongo', tech: 'mongodb' } }
    const { architecture, warnings } = buildArchitecture([...EXAMPLE_NODES, extra], EXAMPLE_EDGES, config)
    expect(architecture.database).toBe('postgres')
    expect(warnings[0]).toMatch(/2 database nodes/)
  })

  it('fails validation without a service node or a name', () => {
    const noServices = EXAMPLE_NODES.filter((n) => n.data.kind !== 'service')
    const r1 = architectureSchema.safeParse(buildArchitecture(noServices, [], config).architecture)
    expect(r1.success).toBe(false)
    const r2 = architectureSchema.safeParse(buildArchitecture(EXAMPLE_NODES, EXAMPLE_EDGES, { ...config, name: '' }).architecture)
    expect(r2.success).toBe(false)
  })
})

describe('slugify', () => {
  it('makes a safe id', () => {
    expect(slugify('  My Shop: v2! ')).toBe('my-shop-v2')
  })
})
