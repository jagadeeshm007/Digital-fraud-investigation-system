import '@xyflow/react/dist/style.css'

import { Background, Controls, ReactFlow, type Edge, type Node } from '@xyflow/react'
import { useEffect, useMemo, useState } from 'react'
import { AutoFit, layout, nodeTypes, TYPE_META, type EntityNodeData } from '@/components/EntityGraph'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
  getCaseGraph,
  getLinks,
  type CaseAlert,
  type CaseGraphData,
  type EntityLinks,
  type EvidenceRecord,
} from '@/lib/api'

// Investigation network for one case (GET /api/graph/case/{id}). Edges join an alert to an identifier
// read from its evidence; an identifier reached by 2+ alerts is the match that grouped them.
// Clicking a node opens its masked records in the side panel.

const humanize = (s: string) => s.replaceAll('_', ' ')
const MASKED = /^\*\*\*-/

export default function CaseGraph({
  caseId,
  primaryAlertId,
  alerts,
  evidence,
}: {
  caseId: string
  primaryAlertId: string
  alerts: CaseAlert[]
  evidence: EvidenceRecord[]
}) {
  const [graph, setGraph] = useState<CaseGraphData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const [sharedOnly, setSharedOnly] = useState(true)

  useEffect(() => {
    let cancelled = false
    setGraph(null)
    getCaseGraph(caseId)
      .then((g) => !cancelled && setGraph(g))
      .catch((e) => !cancelled && setError(e instanceof Error ? e.message : 'Could not load the case network'))
    return () => {
      cancelled = true
    }
  }, [caseId])

  const visible = useMemo<CaseGraphData | null>(() => {
    if (!graph) return null
    if (!sharedOnly) return graph
    const edges = graph.edges.filter((e) => e.shared)
    const keep = new Set([...graph.nodes.filter((n) => n.type === 'alert').map((n) => n.id), ...edges.map((e) => e.target)])
    return { ...graph, nodes: graph.nodes.filter((n) => keep.has(n.id)), edges }
  }, [graph, sharedOnly])

  const { nodes, edges } = useMemo<{ nodes: Node<EntityNodeData>[]; edges: Edge[] }>(() => {
    if (!visible) return { nodes: [], edges: [] }
    const positions = layout(visible, primaryAlertId)
    return {
      nodes: visible.nodes.map((n) => ({
        id: n.id,
        type: 'entity',
        position: positions.get(n.id) ?? { x: 0, y: 0 },
        origin: [0.5, 0.5] as [number, number],
        data: {
          type: n.type,
          label: String(n.data.label ?? n.id),
          focus: n.id === selected,
          hub: Boolean(n.data.shared),
          band: n.type === 'alert' ? (n.data.risk_band as string | undefined) : undefined,
        },
      })),
      edges: visible.edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        type: 'straight',
        label: visible.edges.length <= 40 || e.source === selected || e.target === selected ? e.label : undefined,
        labelStyle: { fontSize: 10 },
        labelBgPadding: [4, 2] as [number, number],
        style: {
          stroke: e.shared ? 'var(--color-warning)' : 'color-mix(in srgb, var(--color-muted-foreground) 55%, transparent)',
          strokeWidth: e.source === selected || e.target === selected ? 3 : e.shared ? 2 : 1.25,
          strokeDasharray: e.shared ? '6 4' : undefined,
        },
      })),
    }
  }, [visible, primaryAlertId, selected])

  if (error) {
    return (
      <Alert variant="error">
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    )
  }
  if (!graph || !visible) return <Skeleton className="h-[460px] w-full" />

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_20rem]">
      <div className="space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-2 text-muted-foreground text-xs">
          <span>
            {visible.nodes.length} entities · {visible.edges.length} links · every link is an identifier read from a
            record, never from the AI
          </span>
          <label className="flex items-center gap-1.5">
            <input type="checkbox" checked={sharedOnly} onChange={(e) => setSharedOnly(e.target.checked)} />
            Only identifiers shared by 2+ alerts
          </label>
        </div>
        <div className="h-[460px] overflow-hidden rounded-lg border bg-muted/40">
          <ReactFlow
            key={`${caseId}-${sharedOnly}`}
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onNodeClick={(_, node) => setSelected(node.id)}
            onPaneClick={() => setSelected(null)}
            nodesConnectable={false}
            fitView
            fitViewOptions={{ padding: 0.15 }}
            minZoom={0.1}
            proOptions={{ hideAttribution: true }}
            aria-label="Case network"
          >
            <Background gap={24} />
            <Controls showInteractive={false} />
            <AutoFit />
          </ReactFlow>
        </div>
        <ul className="flex flex-wrap gap-3 text-muted-foreground text-xs" aria-label="Legend">
          <li className="flex items-center gap-1">
            <span className="inline-block size-3 rounded-sm border-2 border-warning" aria-hidden />
            Matching identifier (shared by 2+ alerts)
          </li>
          <li className="flex items-center gap-1">
            <span className="inline-block size-3 rounded-sm border-2 border-primary" aria-hidden />
            Selected
          </li>
        </ul>
      </div>

      <NodePanel graph={graph} nodeId={selected} alerts={alerts} evidence={evidence} />
    </div>
  )
}

function NodePanel({
  graph,
  nodeId,
  alerts,
  evidence,
}: {
  graph: CaseGraphData
  nodeId: string | null
  alerts: CaseAlert[]
  evidence: EvidenceRecord[]
}) {
  const node = graph.nodes.find((n) => n.id === nodeId)
  const entityId = node && node.type !== 'alert' ? String(node.data.entity_id ?? '') : ''
  const [links, setLinks] = useState<EntityLinks | null>(null)

  useEffect(() => {
    setLinks(null)
    if (!entityId || MASKED.test(entityId)) return
    let cancelled = false
    getLinks(entityId)
      .then((l) => !cancelled && setLinks(l))
      .catch(() => !cancelled && setLinks({ entity_id: entityId, link_count: 0, links: [] }))
    return () => {
      cancelled = true
    }
  }, [entityId])

  if (!node) {
    return (
      <aside className="rounded-lg border p-4 text-muted-foreground text-sm">
        Click an entity in the network to see its records and how it links the alerts.
      </aside>
    )
  }

  const meta = TYPE_META[node.type] ?? { label: humanize(node.type) }
  const nodeEdges = graph.edges.filter((e) => e.source === node.id || e.target === node.id)

  if (node.type === 'alert') {
    const alert = alerts.find((a) => a.alert_id === node.id)
    return (
      <aside className="max-h-[500px] space-y-3 overflow-y-auto rounded-lg border p-4 text-sm" aria-label="Selected entity">
        <div>
          <div className="text-muted-foreground text-xs uppercase tracking-wide">Alert</div>
          <div className="font-medium">{alert?.rule_id ?? node.data.label}</div>
          <div className="text-muted-foreground text-xs">{alert?.fraud_category}</div>
        </div>
        {alert && <p className="text-xs">{alert.link_reason}</p>}
        <ul className="space-y-1">
          {alert?.factors.map((f, i) => (
            <li key={i} className="text-xs">
              <span className="tabular-nums">+{f.points}</span> {f.factor}
            </li>
          ))}
        </ul>
        <div className="text-muted-foreground text-xs">{nodeEdges.length} identifiers in its evidence</div>
      </aside>
    )
  }

  const value = String(node.data.entity_id ?? node.data.label)
  const records = evidence.filter((e) => Object.values(e.record).some((v) => String(v) === value) || e.id === value)
  const viaAlerts = nodeEdges.map((e) => alerts.find((a) => a.alert_id === e.source)).filter(Boolean) as CaseAlert[]

  return (
    <aside className="max-h-[500px] space-y-3 overflow-y-auto rounded-lg border p-4 text-sm" aria-label="Selected entity">
      <div>
        <div className="text-muted-foreground text-xs uppercase tracking-wide">{meta.label}</div>
        <div className="break-all font-mono">{value}</div>
        {viaAlerts.length > 1 && (
          <Badge variant="warning" className="mt-1">
            Links {viaAlerts.length} alerts
          </Badge>
        )}
      </div>

      <section>
        <h4 className="mb-1 font-medium text-xs">Found in the evidence of</h4>
        <ul className="space-y-1 text-xs">
          {nodeEdges.map((e) => (
            <li key={e.id}>
              <span className="font-medium">{alerts.find((a) => a.alert_id === e.source)?.rule_id ?? e.source}</span>
              <span className="text-muted-foreground"> via {e.evidence.join(', ')}</span>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h4 className="mb-1 font-medium text-xs">Records ({records.length})</h4>
        {records.length === 0 ? (
          <p className="text-muted-foreground text-xs">No case record holds this value directly.</p>
        ) : (
          <ul className="space-y-2">
            {records.map((r) => (
              <li key={r.id} className="rounded border bg-muted/40 p-2 text-xs">
                <div className="font-medium">
                  {humanize(r.type)} <span className="font-mono">{r.id}</span>
                </div>
                <dl className="mt-1 grid grid-cols-[max-content_minmax(0,1fr)] gap-x-2">
                  {Object.entries(r.record).map(([k, v]) =>
                    v === null || v === '' ? null : (
                      <div key={k} className="contents">
                        <dt className="text-muted-foreground">{humanize(k)}</dt>
                        <dd className="break-all font-mono">{String(v)}</dd>
                      </div>
                    ),
                  )}
                </dl>
              </li>
            ))}
          </ul>
        )}
      </section>

      {MASKED.test(value) ? (
        <p className="text-muted-foreground text-xs">Masked identifier: matched by token, the raw value is never shown.</p>
      ) : (
        <section>
          <h4 className="mb-1 font-medium text-xs">Elsewhere in the loaded data</h4>
          {!links ? (
            <Skeleton className="h-10 w-full" />
          ) : links.links.length === 0 ? (
            <p className="text-muted-foreground text-xs">No other records share this identifier.</p>
          ) : (
            <ul className="space-y-1 text-xs">
              {links.links.map((l, i) => (
                <li key={i}>
                  <span className="text-muted-foreground">{humanize(l.shared_type)} </span>
                  <span className="font-mono">{l.shared_value}</span>:{' '}
                  {l.linked_entities
                    .slice(0, 8)
                    .map((x) => `${humanize(x.entity_type)} ${x.id}`)
                    .join(', ')}
                  {l.linked_entities.length > 8 && ` +${l.linked_entities.length - 8} more`}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </aside>
  )
}
