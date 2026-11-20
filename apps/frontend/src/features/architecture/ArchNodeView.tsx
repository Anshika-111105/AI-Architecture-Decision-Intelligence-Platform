import { Handle, Position, type NodeProps } from '@xyflow/react'
import { KIND_LABELS, type ArchNode, type NodeKind } from './model'

// Full class names (not built from strings) so Tailwind can find them.
const STYLES: Record<NodeKind, string> = {
  client: 'border-slate-400 bg-slate-100',
  api_gateway: 'border-violet-400 bg-violet-50',
  service: 'border-blue-400 bg-blue-50',
  cache: 'border-amber-400 bg-amber-50',
  database: 'border-emerald-400 bg-emerald-50',
  message_broker: 'border-rose-400 bg-rose-50',
}

// A React Flow "custom node": a normal React component. Handles are the small
// dots where connections attach (target = incoming, source = outgoing).
export default function ArchNodeView({ data, selected }: NodeProps<ArchNode>) {
  return (
    <div
      className={`min-w-36 rounded-lg border-2 px-3 py-2 text-sm shadow-sm ${STYLES[data.kind]} ${selected ? 'ring-2 ring-slate-900' : ''}`}
    >
      <Handle type="target" position={Position.Left} />
      <div className="text-[10px] uppercase tracking-wide text-slate-500">{KIND_LABELS[data.kind]}</div>
      <div className="font-medium">{data.label}</div>
      {data.tech && <div className="text-xs text-slate-600">{data.tech}</div>}
      <Handle type="source" position={Position.Right} />
    </div>
  )
}
