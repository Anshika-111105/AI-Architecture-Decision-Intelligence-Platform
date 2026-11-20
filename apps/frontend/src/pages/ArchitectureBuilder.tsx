import '@xyflow/react/dist/style.css'
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Background,
  Controls,
  MarkerType,
  MiniMap,
  ReactFlow,
  useEdgesState,
  useNodesState,
  type Connection,
  type NodeTypes,
} from '@xyflow/react'
import { useMutation } from '@tanstack/react-query'
import { api } from '../lib/api'
import { architectureSchema } from '../types/architecture.zod'
import ArchNodeView from '../features/architecture/ArchNodeView'
import { buildArchitecture } from '../features/architecture/buildArchitecture'
import { EXAMPLE_EDGES, EXAMPLE_NODES } from '../features/architecture/exampleGraph'
import {
  COMMUNICATIONS,
  DEFAULT_CONFIG,
  DEFAULT_TECH,
  ENUMS,
  KIND_LABELS,
  NODE_KINDS,
  TECH_OPTIONS,
  type ArchEdge,
  type ArchNode,
  type BuilderConfig,
  type NodeKind,
} from '../features/architecture/model'

// Defined outside the component so React Flow does not see a "new" object every render.
const nodeTypes: NodeTypes = { arch: ArchNodeView }

const DRAFT_KEY = 'adip.architectureDraft'

interface Draft {
  nodes: ArchNode[]
  edges: ArchEdge[]
  config: BuilderConfig
}

function loadDraft(): Draft | null {
  try {
    const raw = localStorage.getItem(DRAFT_KEY)
    if (!raw) return null
    const d = JSON.parse(raw) as Draft
    return Array.isArray(d.nodes) && Array.isArray(d.edges) && d.config ? d : null
  } catch {
    return null
  }
}

function Select({
  label,
  value,
  options,
  onChange,
}: {
  label: string
  value: string
  options: readonly string[]
  onChange: (v: string) => void
}) {
  const id = `sel-${label.replace(/\W+/g, '-')}`
  return (
    <div>
      <label htmlFor={id} className="block text-xs font-medium">{label}</label>
      <select id={id} value={value} onChange={(e) => onChange(e.target.value)} className="mt-1 w-full rounded border border-slate-300 bg-white px-2 py-1.5 text-sm">
        {options.map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
    </div>
  )
}

export default function ArchitectureBuilder() {
  const [draft] = useState(loadDraft)
  const [nodes, setNodes, onNodesChange] = useNodesState<ArchNode>(draft?.nodes ?? [])
  const [edges, setEdges, onEdgesChange] = useEdgesState<ArchEdge>(draft?.edges ?? [])
  const [config, setConfig] = useState<BuilderConfig>(draft?.config ?? DEFAULT_CONFIG)
  const [linkType, setLinkType] = useState<string>('HTTP')
  const [selected, setSelected] = useState<{ type: 'node' | 'edge'; id: string } | null>(null)

  // Keep the work in progress when the user navigates away or reloads.
  useEffect(() => {
    try {
      localStorage.setItem(DRAFT_KEY, JSON.stringify({ nodes, edges, config }))
    } catch {
      /* storage unavailable: the draft just won't be restored */
    }
  }, [nodes, edges, config])

  const built = useMemo(() => buildArchitecture(nodes, edges, config), [nodes, edges, config])
  const validation = useMemo(() => architectureSchema.safeParse(built.architecture), [built])
  const issues = validation.success ? [] : validation.error.issues.map((i) => `${i.path.map(String).join('.')}: ${i.message}`)

  const save = useMutation({
    mutationFn: () =>
      api('/architectures', { method: 'POST', body: JSON.stringify({ architecture: built.architecture, graph: built.graph }) }),
  })

  const selectedNode = selected?.type === 'node' ? nodes.find((n) => n.id === selected.id) : undefined
  const selectedEdge = selected?.type === 'edge' ? edges.find((e) => e.id === selected.id) : undefined

  function addNode(kind: NodeKind) {
    const id = `${kind}-${Date.now().toString(36)}`
    const count = nodes.filter((n) => n.data.kind === kind).length
    const tech = DEFAULT_TECH[kind]
    setNodes((ns) => [
      ...ns,
      {
        id,
        type: 'arch',
        position: { x: 60 + (ns.length % 4) * 200, y: 40 + Math.floor(ns.length / 4) * 110 },
        data: { kind, label: `${KIND_LABELS[kind]} ${count + 1}`, ...(tech ? { tech } : {}) },
      },
    ])
  }

  function onConnect(c: Connection) {
    if (!c.source || !c.target || c.source === c.target) return
    const id = `${c.source}->${c.target}`
    setEdges((es) =>
      es.some((e) => e.id === id)
        ? es
        : [...es, { id, source: c.source, target: c.target, label: linkType, data: { communication: linkType }, markerEnd: { type: MarkerType.ArrowClosed } }],
    )
  }

  function patchNode(id: string, patch: Partial<ArchNode['data']>) {
    setNodes((ns) => ns.map((n) => (n.id === id ? { ...n, data: { ...n.data, ...patch } } : n)))
  }

  function setEdgeCommunication(id: string, communication: string) {
    setEdges((es) => es.map((e) => (e.id === id ? { ...e, label: communication, data: { communication } } : e)))
  }

  function deleteSelected() {
    if (!selected) return
    if (selected.type === 'node') {
      setNodes((ns) => ns.filter((n) => n.id !== selected.id))
      setEdges((es) => es.filter((e) => e.source !== selected.id && e.target !== selected.id))
    } else {
      setEdges((es) => es.filter((e) => e.id !== selected.id))
    }
    setSelected(null)
  }

  function loadExample() {
    setNodes(EXAMPLE_NODES)
    setEdges(EXAMPLE_EDGES)
    setConfig((c) => ({ ...c, name: c.name || 'Example shop' }))
    setSelected(null)
  }

  function clearCanvas() {
    if (nodes.length > 0 && !window.confirm('Remove everything from the canvas?')) return
    setNodes([])
    setEdges([])
    setSelected(null)
  }

  const setCfg = <K extends keyof BuilderConfig>(key: K, value: BuilderConfig[K]) => setConfig((c) => ({ ...c, [key]: value }))

  return (
    <div>
      <h1 className="text-2xl font-semibold">Architecture Builder</h1>
      <p className="mt-2 text-slate-600">
        Add components, drag from one dot to another to connect them, then review the exported architecture on the right.
      </p>

      <div className="mt-6 grid gap-4 lg:grid-cols-[13rem_minmax(0,1fr)_21rem]">
        {/* Palette */}
        <aside className="space-y-2">
          <h2 className="text-sm font-medium">Add component</h2>
          {NODE_KINDS.map((k) => (
            <button key={k} type="button" onClick={() => addNode(k)} className="block w-full rounded border border-slate-300 bg-white px-3 py-2 text-left text-sm hover:border-slate-500">
              + {KIND_LABELS[k]}
            </button>
          ))}
          <div className="pt-2">
            <label htmlFor="linkType" className="block text-xs font-medium">Type for new connections</label>
            <select id="linkType" value={linkType} onChange={(e) => setLinkType(e.target.value)} className="mt-1 w-full rounded border border-slate-300 bg-white px-2 py-1.5 text-sm">
              {COMMUNICATIONS.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <button type="button" onClick={loadExample} className="mt-2 block w-full rounded border border-slate-900 px-3 py-2 text-sm hover:bg-slate-100">
            Load README example
          </button>
          <button type="button" onClick={clearCanvas} className="block w-full rounded border border-slate-300 px-3 py-2 text-sm text-slate-600 hover:bg-slate-100">
            Clear canvas
          </button>
        </aside>

        {/* Canvas (React Flow needs a parent with an explicit height) */}
        <div className="h-[560px] rounded-lg border border-slate-200 bg-white">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={(_, n) => setSelected({ type: 'node', id: n.id })}
            onEdgeClick={(_, e) => setSelected({ type: 'edge', id: e.id })}
            onPaneClick={() => setSelected(null)}
            fitView
          >
            <Background />
            <Controls />
            <MiniMap pannable zoomable />
          </ReactFlow>
        </div>

        {/* Right panel */}
        <aside className="space-y-4">
          {(selectedNode || selectedEdge) && (
            <section className="rounded-lg border border-slate-200 bg-white p-3">
              <h2 className="text-sm font-medium">Selected {selectedNode ? 'component' : 'connection'}</h2>
              {selectedNode && (
                <div className="mt-2 space-y-2">
                  <div>
                    <label htmlFor="nodeLabel" className="block text-xs font-medium">Name</label>
                    <input id="nodeLabel" value={selectedNode.data.label} onChange={(e) => patchNode(selectedNode.id, { label: e.target.value })} className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-sm" />
                  </div>
                  {TECH_OPTIONS[selectedNode.data.kind] && (
                    <Select label="Technology" value={selectedNode.data.tech ?? ''} options={TECH_OPTIONS[selectedNode.data.kind]!} onChange={(v) => patchNode(selectedNode.id, { tech: v })} />
                  )}
                </div>
              )}
              {selectedEdge && (
                <div className="mt-2">
                  <Select label="Communication" value={selectedEdge.data?.communication ?? 'HTTP'} options={COMMUNICATIONS} onChange={(v) => setEdgeCommunication(selectedEdge.id, v)} />
                </div>
              )}
              <button type="button" onClick={deleteSelected} className="mt-3 rounded border border-red-300 px-3 py-1.5 text-sm text-red-700 hover:bg-red-50">
                Delete
              </button>
            </section>
          )}

          <section className="space-y-2 rounded-lg border border-slate-200 bg-white p-3">
            <h2 className="text-sm font-medium">Architecture settings</h2>
            <div>
              <label htmlFor="archName" className="block text-xs font-medium">Name</label>
              <input id="archName" value={config.name} onChange={(e) => setCfg('name', e.target.value)} placeholder="e.g. Shop v1" className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-sm" />
            </div>
            <Select label="Pattern" value={config.architecture_pattern} options={ENUMS.architecture_pattern} onChange={(v) => setCfg('architecture_pattern', v)} />
            <Select label="Style" value={config.architecture_style} options={ENUMS.architecture_style} onChange={(v) => setCfg('architecture_style', v)} />
            <Select label="API style" value={config.api_style} options={ENUMS.api_style} onChange={(v) => setCfg('api_style', v)} />
            <Select label="Deployment" value={config.deployment} options={ENUMS.deployment} onChange={(v) => setCfg('deployment', v)} />
            <Select label="Cloud" value={config.cloud} options={ENUMS.cloud} onChange={(v) => setCfg('cloud', v)} />
            <div className="grid grid-cols-3 gap-2">
              <div>
                <label htmlFor="replicas" className="block text-xs font-medium">Replicas</label>
                <input id="replicas" type="number" value={config.replica_count} onChange={(e) => setCfg('replica_count', Number(e.target.value))} className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-sm" />
              </div>
              <div>
                <label htmlFor="cpu" className="block text-xs font-medium">vCPU</label>
                <input id="cpu" type="number" step="any" value={config.cpu_limit} onChange={(e) => setCfg('cpu_limit', Number(e.target.value))} className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-sm" />
              </div>
              <div>
                <label htmlFor="mem" className="block text-xs font-medium">Memory GB</label>
                <input id="mem" type="number" step="any" value={config.memory_limit} onChange={(e) => setCfg('memory_limit', Number(e.target.value))} className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-sm" />
              </div>
            </div>
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-3 text-sm">
            <h2 className="font-medium">Derived from your graph</h2>
            <p className="mt-1 text-xs text-slate-600">
              {built.architecture.service_count} services, database {built.architecture.database}, cache {built.architecture.cache}, messaging {built.architecture.messaging}, {built.architecture.node_count} nodes, {built.architecture.edge_count} edges
            </p>
            {built.warnings.map((w) => <p key={w} className="mt-1 text-xs text-amber-700">{w}</p>)}
            {issues.length > 0 && (
              <ul role="alert" className="mt-2 list-disc pl-5 text-xs text-red-600">
                {issues.map((i) => <li key={i}>{i}</li>)}
              </ul>
            )}
            <button type="button" disabled={issues.length > 0 || save.isPending} onClick={() => save.mutate()} className="mt-3 rounded bg-slate-900 px-4 py-2 text-white hover:bg-slate-700 disabled:opacity-50">
              {save.isPending ? 'Saving...' : 'Save architecture'}
            </button>
            {save.isError && <p role="alert" className="mt-2 text-xs text-red-600">Could not save: {save.error.message}</p>}
            {save.isSuccess && (
              <p className="mt-2 rounded border border-green-300 bg-green-50 px-3 py-2 text-xs text-green-900">
                Architecture saved. Next: <Link to="/compare" className="font-medium underline">compare architectures</Link>.
              </p>
            )}
            <details className="mt-3">
              <summary className="cursor-pointer text-xs font-medium">Show exported JSON</summary>
              <pre className="mt-2 max-h-64 overflow-auto rounded bg-slate-50 p-2 text-[11px]">
                {JSON.stringify({ architecture: built.architecture, graph: built.graph }, null, 2)}
              </pre>
            </details>
          </section>
        </aside>
      </div>
    </div>
  )
}
