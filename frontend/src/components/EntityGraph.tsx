import '@xyflow/react/dist/style.css'

import {
  Background,
  Controls,
  Handle,
  Position,
  ReactFlow,
  useNodesInitialized,
  useReactFlow,
  useStore,
  type Edge,
  type Node,
  type NodeProps,
} from '@xyflow/react'
import {
  ArrowLeftRightIcon,
  CreditCardIcon,
  FileTextIcon,
  GlobeIcon,
  LogInIcon,
  ShieldAlertIcon,
  SirenIcon,
  SmartphoneIcon,
  UndoIcon,
  UserIcon,
  UserPlusIcon,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from '@/components/ui/empty'
import { Skeleton } from '@/components/ui/skeleton'
import { getGraph, type EntityGraphData, type GraphNodeType } from '@/lib/api'

// EntityGraph per inception/refined-mockups/interaction-spec.md: typed nodes with masked labels,
// edges for shared identifiers, a layered left-to-right layout, and a keyboard-reachable text list of the links.
// Data comes from GET /api/graph/alert/{id} and /api/graph/entity/{id} (app/graph/builder.py).

const TYPE_META: Record<GraphNodeType, { label: string; icon: typeof UserIcon }> = {
  alert: { label: 'Alert', icon: SirenIcon },
  customer: { label: 'Customer', icon: UserIcon },
  account: { label: 'Account', icon: CreditCardIcon },
  transaction: { label: 'Transaction', icon: ArrowLeftRightIcon },
  device: { label: 'Device', icon: SmartphoneIcon },
  ip_address: { label: 'IP address', icon: GlobeIcon },
  login_event: { label: 'Login', icon: LogInIcon },
  beneficiary_change: { label: 'Payee change', icon: UserPlusIcon },
  loan_application: { label: 'Loan application', icon: FileTextIcon },
  insurance_claim: { label: 'Insurance claim', icon: ShieldAlertIcon },
}

// A device or IP used across many records or customers is the shared identifier the spec asks to surface.
const HUB_TYPES = new Set<GraphNodeType>(['device', 'ip_address'])

const humanize = (s: string) => s.replaceAll('_', ' ')

// Layered layout: the focus entity in column 0, its direct links in column 1, and so on.
// Fixed-size cards and wide column gaps keep nodes apart and leave room for edge labels.
const NODE_W = 196
const COL_GAP = 300
const ROW_GAP = 72

function layout(
  data: EntityGraphData,
  focus: string,
): { pos: Map<string, { x: number; y: number }>; depth: Map<string, number> } {
  const adj = new Map<string, string[]>(data.nodes.map((n) => [n.id, []]))
  for (const e of data.edges) {
    adj.get(e.source)?.push(e.target)
    adj.get(e.target)?.push(e.source)
  }
  const depth = new Map<string, number>()
  const queue = adj.has(focus) ? [focus] : []
  if (queue.length) depth.set(focus, 0)
  for (let i = 0; i < queue.length; i++) {
    for (const nb of adj.get(queue[i]) ?? []) {
      if (!depth.has(nb)) {
        depth.set(nb, depth.get(queue[i])! + 1)
        queue.push(nb)
      }
    }
  }
  const last = Math.max(0, ...depth.values()) + 1
  for (const n of data.nodes) if (!depth.has(n.id)) depth.set(n.id, last) // unreachable: own column

  const typeOf = new Map(data.nodes.map((n) => [n.id, n.type]))
  const columns: string[][] = []
  for (const n of data.nodes) (columns[depth.get(n.id)!] ??= []).push(n.id)

  // Order each column by the average row of its neighbours in the previous column (fewer crossings).
  const row = new Map<string, number>()
  columns.forEach((col, d) => {
    const score = (id: string) => {
      const prev = (adj.get(id) ?? []).filter((nb) => depth.get(nb) === d - 1).map((nb) => row.get(nb) ?? 0)
      return prev.length ? prev.reduce((a, b) => a + b, 0) / prev.length : 0
    }
    col.sort(
      (a, b) => score(a) - score(b) || String(typeOf.get(a)).localeCompare(String(typeOf.get(b))) || a.localeCompare(b),
    )
    col.forEach((id, i) => row.set(id, i))
  })

  const pos = new Map<string, { x: number; y: number }>()
  columns.forEach((col, d) =>
    col.forEach((id, i) => pos.set(id, { x: d * COL_GAP, y: (i - (col.length - 1) / 2) * ROW_GAP })),
  )
  return { pos, depth }
}

/** Device / IP nodes with 3+ links, or reaching 2+ customers directly or via one record. */
function sharedHubs(data: EntityGraphData): Set<string> {
  const type = new Map(data.nodes.map((n) => [n.id, n.type]))
  const adj = new Map<string, Set<string>>()
  for (const e of data.edges) {
    if (!adj.has(e.source)) adj.set(e.source, new Set())
    if (!adj.has(e.target)) adj.set(e.target, new Set())
    adj.get(e.source)!.add(e.target)
    adj.get(e.target)!.add(e.source)
  }
  const hubs = new Set<string>()
  for (const n of data.nodes) {
    if (!HUB_TYPES.has(n.type)) continue
    const customers = new Set<string>()
    for (const a of adj.get(n.id) ?? []) {
      if (type.get(a) === 'customer') customers.add(a)
      for (const b of adj.get(a) ?? []) if (type.get(b) === 'customer') customers.add(b)
    }
    if (customers.size >= 2 || (adj.get(n.id)?.size ?? 0) >= 3) hubs.add(n.id)
  }
  return hubs
}

type EntityNodeData = { type: GraphNodeType; label: string; focus: boolean; hub: boolean; band?: string }

function EntityNode({ data }: NodeProps<Node<EntityNodeData>>) {
  const meta = TYPE_META[data.type] ?? { label: humanize(data.type), icon: UserIcon }
  const Icon = meta.icon
  const ring = data.focus ? 'border-primary ring-2 ring-mint' : data.hub ? 'border-warning ring-2 ring-warning/30' : ''
  return (
    <div
      className={`flex items-center gap-2 rounded-lg border bg-card px-2.5 py-1.5 shadow-xs ${ring}`}
      style={{ width: NODE_W }}
      title={`${meta.label}: ${data.label}`}
    >
      {/* Edges enter on the left and leave on the right, so they run between columns, not across cards. */}
      <Handle type="target" position={Position.Left} className="!opacity-0" isConnectable={false} />
      <Handle type="source" position={Position.Right} className="!opacity-0" isConnectable={false} />
      <span
        className={`rounded-md p-1 ${
          data.focus ? 'bg-primary text-primary-foreground' : data.type === 'alert' ? 'bg-destructive/15' : 'bg-muted'
        }`}
      >
        <Icon className="size-4" aria-hidden />
      </span>
      <span className="min-w-0 flex-1 leading-tight">
        <span className="block truncate text-[10px] text-muted-foreground uppercase tracking-wide">
          {meta.label}
          {data.band && ` · ${data.band}`}
        </span>
        <span className="block truncate font-mono text-xs">{data.label}</span>
      </span>
    </div>
  )
}

const nodeTypes = { entity: EntityNode }

/** Re-fits once nodes are measured and whenever the panel resizes (lazy CSS, grid reflow, sidebar toggle). */
function AutoFit() {
  const { fitView } = useReactFlow()
  const initialized = useNodesInitialized()
  const width = useStore((s) => s.width)
  const height = useStore((s) => s.height)
  useEffect(() => {
    if (!initialized || !width || !height) return
    // Node sizes settle a frame after measurement and again once web fonts load; fit after both.
    const fit = () => void fitView({ padding: 0.15 })
    const frame = requestAnimationFrame(() => requestAnimationFrame(fit))
    const settle = window.setTimeout(fit, 250)
    void document.fonts?.ready.then(fit)
    return () => {
      cancelAnimationFrame(frame)
      window.clearTimeout(settle)
    }
  }, [initialized, width, height, fitView])
  return null
}

export default function EntityGraph({ alertId }: { alertId: string }) {
  // null focus = the alert's own evidence graph; otherwise an entity the user clicked.
  const [focus, setFocus] = useState<string | null>(null)
  const [graph, setGraph] = useState<EntityGraphData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [highlight, setHighlight] = useState<string | null>(null)

  useEffect(() => setFocus(null), [alertId])

  useEffect(() => {
    let cancelled = false
    setGraph(null)
    setError(null)
    ;(focus ? getGraph('entity', focus) : getGraph('alert', alertId))
      .then((g) => !cancelled && setGraph(g))
      .catch((e) => !cancelled && setError(e instanceof Error ? e.message : 'Could not load related entities'))
    return () => {
      cancelled = true
    }
  }, [alertId, focus])

  const centre = focus ?? alertId
  const labelOf = useMemo(() => new Map(graph?.nodes.map((n) => [n.id, n]) ?? []), [graph])

  const { nodes, edges } = useMemo<{ nodes: Node<EntityNodeData>[]; edges: Edge[] }>(() => {
    if (!graph) return { nodes: [], edges: [] }
    const { pos: positions, depth } = layout(graph, centre)
    const hubs = sharedHubs(graph)
    const showLabels = graph.edges.length <= 30
    return {
      nodes: graph.nodes.map((n) => ({
        id: n.id,
        type: 'entity',
        position: positions.get(n.id) ?? { x: 0, y: 0 },
        origin: [0, 0.5] as [number, number],
        data: {
          type: n.type,
          label: String(n.data.label ?? n.id),
          focus: n.id === centre,
          hub: hubs.has(n.id),
          band: n.type === 'alert' ? (n.data.risk_band as string | undefined) : undefined,
        },
      })),
      edges: graph.edges.map((e) => {
        const loud = hubs.has(e.source) || hubs.has(e.target)
        const active = highlight === e.id
        // Draw every edge left to right; the text list keeps the original direction.
        const flip = (depth.get(e.source) ?? 0) > (depth.get(e.target) ?? 0)
        return {
          id: e.id,
          source: flip ? e.target : e.source,
          target: flip ? e.source : e.target,
          type: 'default',
          label: showLabels || active ? humanize(e.label) : undefined,
          animated: active,
          labelStyle: { fontSize: 10, fill: 'var(--color-muted-foreground)' },
          labelBgStyle: { fill: 'var(--color-card)' },
          labelBgPadding: [4, 2] as [number, number],
          labelBgBorderRadius: 4,
          style: {
            stroke: loud
              ? 'var(--color-warning)'
              : 'color-mix(in srgb, var(--color-muted-foreground) 55%, transparent)',
            strokeWidth: active ? 3 : loud ? 2 : 1.25,
            strokeDasharray: loud ? '6 4' : undefined,
          },
        }
      }),
    }
  }, [graph, centre, highlight])

  if (error) {
    return (
      <Alert variant="error">
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    )
  }
  if (!graph) return <Skeleton className="h-[420px] w-full" />
  if (graph.edges.length === 0) {
    return (
      <Empty className="rounded-lg border border-dashed">
        <EmptyHeader>
          <EmptyTitle>No linked entities</EmptyTitle>
          <EmptyDescription>Nothing in the loaded data links to {centre}.</EmptyDescription>
        </EmptyHeader>
      </Empty>
    )
  }

  const describe = (id: string) => {
    const n = labelOf.get(id)
    return n ? `${TYPE_META[n.type]?.label ?? humanize(n.type)} ${n.data.label ?? id}` : id
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_18rem]">
      <div className="space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-2 text-muted-foreground text-xs">
          <span>
            {focus ? (
              <>
                Centred on <span className="font-mono text-foreground">{describe(focus)}</span>
              </>
            ) : (
              'Evidence for this alert'
            )}{' '}
            · {graph.nodes.length} entities · click an entity to explore from it
          </span>
          {focus && (
            <Button size="xs" variant="outline" onClick={() => setFocus(null)}>
              <UndoIcon />
              Back to alert
            </Button>
          )}
        </div>
        <div className="h-[420px] overflow-hidden rounded-lg border bg-muted/40">
          <ReactFlow
            key={centre}
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onNodeClick={(_, node) => setFocus(node.id === alertId ? null : node.id)}
            nodesConnectable={false}
            fitView
            fitViewOptions={{ padding: 0.15 }}
            minZoom={0.1}
            // The mouse wheel scrolls the page; zoom with the controls or a pinch.
            zoomOnScroll={false}
            preventScrolling={false}
            proOptions={{ hideAttribution: true }}
            aria-label="Entity graph"
          >
            <Background gap={24} />
            <Controls showInteractive={false} />
            <AutoFit />
          </ReactFlow>
        </div>
        <ul className="flex flex-wrap gap-3 text-muted-foreground text-xs" aria-label="Legend">
          <li className="flex items-center gap-1">
            <span className="inline-block size-3 rounded-sm border-2 border-warning" aria-hidden />
            Shared device or IP
          </li>
          <li className="flex items-center gap-1">
            <span className="inline-block size-3 rounded-sm border-2 border-primary" aria-hidden />
            Current centre
          </li>
        </ul>
      </div>

      <section aria-label="Links as text" className="max-h-[470px] overflow-y-auto rounded-lg border">
        <h3 className="sticky top-0 border-b bg-card px-3 py-2 font-medium text-sm">Links ({graph.edges.length})</h3>
        <ul>
          {graph.edges.map((e) => (
            <li
              key={e.id}
              tabIndex={0}
              onFocus={() => setHighlight(e.id)}
              onBlur={() => setHighlight(null)}
              onMouseEnter={() => setHighlight(e.id)}
              onMouseLeave={() => setHighlight(null)}
              className="border-b px-3 py-2 text-xs outline-none last:border-b-0 focus-visible:bg-accent hover:bg-accent"
            >
              <span className="font-medium">{describe(e.source)}</span>
              <span className="text-muted-foreground"> {humanize(e.label)} </span>
              <span className="font-medium">{describe(e.target)}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
