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
  forceCenter,
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
  type SimulationLinkDatum,
  type SimulationNodeDatum,
} from 'd3-force'
import { CreditCardIcon, FileTextIcon, ShieldAlertIcon, SmartphoneIcon, UndoIcon, UserIcon } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from '@/components/ui/empty'
import { Skeleton } from '@/components/ui/skeleton'
import { getLinks, type EntityLink, type EntityType, type GraphNode, type LinkGraph } from '@/lib/api'

// EntityGraph per inception/refined-mockups/interaction-spec.md: typed nodes, shared-identifier
// edges, d3-force layout, and a keyboard-reachable text list of the same links.

const TYPE_META: Record<EntityType, { label: string; icon: typeof UserIcon }> = {
  customer: { label: 'Customer', icon: UserIcon },
  account: { label: 'Account', icon: CreditCardIcon },
  device: { label: 'Device', icon: SmartphoneIcon },
  application: { label: 'Loan application', icon: FileTextIcon },
  claim: { label: 'Insurance claim', icon: ShieldAlertIcon },
}

const ATTRIBUTE_LABELS: Record<string, string> = {
  account_owner: 'owns',
  device: 'uses device',
  applicant: 'applied',
  disbursement_account: 'disbursed to',
  claimant: 'claimed',
  payout_account: 'paid out to',
  transfer: 'sent money',
  payee_added: 'added payee',
  phone: 'same phone',
  email: 'same email',
  ip_address: 'same IP',
}

// Identifiers that tie two different people together are the fraud signal; draw them louder.
const SHARED_IDENTITY = new Set(['phone', 'email', 'ip_address'])

const nodeKey = (type: string, id: string) => `${type}:${id}`

export function linkLabel(link: EntityLink): string {
  const base = ATTRIBUTE_LABELS[link.shared_attribute] ?? link.shared_attribute.replaceAll('_', ' ')
  const value = link.shared_value_masked ? ` ${link.shared_value_masked}` : ''
  const times = link.count > 1 ? ` ×${link.count}` : ''
  return `${base}${value}${times}`
}

type SimNode = SimulationNodeDatum & { key: string; focus: boolean }

/** Runs d3-force to completion synchronously; the focus entity is pinned at the centre. */
function layout(nodes: GraphNode[], links: EntityLink[]): Map<string, { x: number; y: number }> {
  const simNodes: SimNode[] = nodes.map((n) => ({
    key: n.key,
    focus: n.is_focus,
    ...(n.is_focus ? { fx: 0, fy: 0 } : {}),
  }))
  const simLinks: SimulationLinkDatum<SimNode>[] = links.map((l) => ({
    source: nodeKey(l.from_type, l.from_id),
    target: nodeKey(l.to_type, l.to_id),
  }))
  const sim = forceSimulation(simNodes)
    .force(
      'link',
      forceLink<SimNode, SimulationLinkDatum<SimNode>>(simLinks)
        .id((d) => d.key)
        .distance(150),
    )
    .force('charge', forceManyBody().strength(-700))
    .force('collide', forceCollide(70))
    .force('center', forceCenter(0, 0))
    .stop()
  sim.tick(300)
  return new Map(simNodes.map((n) => [n.key, { x: n.x ?? 0, y: n.y ?? 0 }]))
}

type EntityNodeData = { type: EntityType; id: string; focus: boolean }

function EntityNode({ data }: NodeProps<Node<EntityNodeData>>) {
  const meta = TYPE_META[data.type] ?? TYPE_META.customer
  const Icon = meta.icon
  return (
    <div
      className={`flex items-center gap-2 rounded-lg border bg-card px-2.5 py-1.5 shadow-xs ${
        data.focus ? 'border-primary ring-2 ring-mint' : ''
      }`}
    >
      {/* Edges run centre to centre, so both handles sit invisibly in the middle. */}
      <Handle type="target" position={Position.Top} className="!top-1/2 !left-1/2 !opacity-0" isConnectable={false} />
      <Handle type="source" position={Position.Top} className="!top-1/2 !left-1/2 !opacity-0" isConnectable={false} />
      <span className={`rounded-md p-1 ${data.focus ? 'bg-primary text-primary-foreground' : 'bg-muted'}`}>
        <Icon className="size-4" aria-hidden />
      </span>
      <span className="leading-tight">
        <span className="block text-[10px] text-muted-foreground uppercase tracking-wide">{meta.label}</span>
        <span className="block font-mono text-xs">{data.id}</span>
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
    void document.fonts?.ready.then(fit)
    return () => cancelAnimationFrame(frame)
  }, [initialized, width, height, fitView])
  return null
}

export default function EntityGraph({ entityId }: { entityId: string }) {
  const [focusId, setFocusId] = useState(entityId)
  const [graph, setGraph] = useState<LinkGraph | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [highlight, setHighlight] = useState<string | null>(null)

  useEffect(() => setFocusId(entityId), [entityId])

  useEffect(() => {
    let cancelled = false
    setGraph(null)
    setError(null)
    getLinks(focusId)
      .then((g) => !cancelled && setGraph(g))
      .catch((e) => !cancelled && setError(e instanceof Error ? e.message : 'Could not load related entities'))
    return () => {
      cancelled = true
    }
  }, [focusId])

  const { nodes, edges } = useMemo<{ nodes: Node<EntityNodeData>[]; edges: Edge[] }>(() => {
    if (!graph) return { nodes: [] as Node<EntityNodeData>[], edges: [] as Edge[] }
    const positions = layout(graph.nodes, graph.links)
    const showLabels = graph.links.length <= 30
    return {
      nodes: graph.nodes.map((n) => ({
        id: n.key,
        type: 'entity',
        position: positions.get(n.key) ?? { x: 0, y: 0 },
        origin: [0.5, 0.5] as [number, number],
        data: { type: n.type, id: n.id, focus: n.is_focus },
      })),
      edges: graph.links.map((l) => {
        const loud = SHARED_IDENTITY.has(l.shared_attribute)
        const active = highlight === l.link_id
        return {
          id: l.link_id,
          source: nodeKey(l.from_type, l.from_id),
          target: nodeKey(l.to_type, l.to_id),
          type: 'straight',
          label: showLabels || active ? linkLabel(l) : undefined,
          animated: active,
          labelStyle: { fontSize: 10 },
          labelBgPadding: [4, 2] as [number, number],
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
  }, [graph, highlight])

  if (error) {
    return (
      <Alert variant="error">
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    )
  }
  if (!graph) return <Skeleton className="h-[420px] w-full" />
  if (graph.links.length === 0) {
    return (
      <Empty className="rounded-lg border border-dashed">
        <EmptyHeader>
          <EmptyTitle>No linked entities</EmptyTitle>
          <EmptyDescription>Nothing in the loaded data shares an identifier with {focusId}.</EmptyDescription>
        </EmptyHeader>
      </Empty>
    )
  }

  const nodeName = (type: EntityType, id: string) => `${TYPE_META[type]?.label ?? type} ${id}`

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_18rem]">
      <div className="space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-2 text-muted-foreground text-xs">
          <span>
            Centred on <span className="font-mono text-foreground">{focusId}</span> · {graph.nodes.length} entities ·
            click an entity to explore from it
            {graph.truncated && ' · showing the nearest 60'}
          </span>
          {focusId !== entityId && (
            <Button size="xs" variant="outline" onClick={() => setFocusId(entityId)}>
              <UndoIcon />
              Back to {entityId}
            </Button>
          )}
        </div>
        <div className="h-[420px] overflow-hidden rounded-lg border bg-muted/40">
          <ReactFlow
            key={focusId}
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onNodeClick={(_, node) => setFocusId((node.data as EntityNodeData).id)}
            nodesConnectable={false}
            fitView
            fitViewOptions={{ padding: 0.2 }}
            minZoom={0.2}
            proOptions={{ hideAttribution: true }}
            aria-label={`Entity graph centred on ${focusId}`}
          >
            <Background gap={24} />
            <Controls showInteractive={false} />
            <AutoFit />
          </ReactFlow>
        </div>
        <ul className="flex flex-wrap gap-3 text-muted-foreground text-xs" aria-label="Legend">
          {Object.entries(TYPE_META).map(([type, meta]) => (
            <li key={type} className="flex items-center gap-1">
              <meta.icon className="size-3.5" aria-hidden />
              {meta.label}
            </li>
          ))}
          <li className="flex items-center gap-1">
            <span className="inline-block w-5 border-warning border-t-2 border-dashed" aria-hidden />
            Shared phone, email or IP
          </li>
        </ul>
      </div>

      <section aria-label="Links as text" className="max-h-[470px] overflow-y-auto rounded-lg border">
        <h3 className="sticky top-0 border-b bg-card px-3 py-2 font-medium text-sm">Links ({graph.links.length})</h3>
        <ul>
          {graph.links.map((l) => (
            <li
              key={l.link_id}
              tabIndex={0}
              onFocus={() => setHighlight(l.link_id)}
              onBlur={() => setHighlight(null)}
              onMouseEnter={() => setHighlight(l.link_id)}
              onMouseLeave={() => setHighlight(null)}
              className="border-b px-3 py-2 text-xs outline-none last:border-b-0 focus-visible:bg-accent hover:bg-accent"
            >
              <span className="font-medium">{nodeName(l.from_type, l.from_id)}</span>
              <span
                className={
                  SHARED_IDENTITY.has(l.shared_attribute) ? 'text-warning-foreground' : 'text-muted-foreground'
                }
              >
                {' '}
                {linkLabel(l)}{' '}
              </span>
              <span className="font-medium">{nodeName(l.to_type, l.to_id)}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
