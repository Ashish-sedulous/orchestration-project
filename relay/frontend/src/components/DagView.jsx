import { agentColor } from '../theme'

const W = 210, H = 74, GX = 80, GY = 22, PAD = 18

function layout(nodes) {
  const byId = Object.fromEntries(nodes.map((n) => [n.id, n]))
  const level = {}
  const lv = (id) => {
    if (level[id] !== undefined) return level[id]
    const deps = (byId[id].depends_on || []).filter((d) => byId[d])
    level[id] = deps.length ? 1 + Math.max(...deps.map(lv)) : 0
    return level[id]
  }
  nodes.forEach((n) => lv(n.id))
  const cols = {}
  nodes.forEach((n) => { (cols[level[n.id]] ||= []).push(n.id) })
  const colKeys = Object.keys(cols).map(Number)
  const maxRows = Math.max(...Object.values(cols).map((c) => c.length))
  const total = maxRows * H + (maxRows - 1) * GY
  const pos = {}
  colKeys.forEach((l) => {
    const ids = cols[l]
    const colH = ids.length * H + (ids.length - 1) * GY
    ids.forEach((id, i) => { pos[id] = { x: PAD + l * (W + GX), y: PAD + (total - colH) / 2 + i * (H + GY) } })
  })
  return {
    pos,
    width: PAD * 2 + colKeys.length * W + (colKeys.length - 1) * GX,
    height: PAD * 2 + total,
  }
}

const clip = (s, n) => (s.length > n ? s.slice(0, n - 1) + '...' : s)

export default function DagView({ state }) {
  const nodes = state.order.map((id) => state.nodes[id])
  if (!nodes.length) {
    return (
      <div className="flex h-44 items-center justify-center rounded-2xl border border-dashed border-line text-sm text-muted">
        {state.status === 'running' ? 'Analyzing the task and building the workflow...' : 'The workflow graph appears here when a run starts.'}
      </div>
    )
  }
  const { pos, width, height } = layout(nodes)

  return (
    <div className="overflow-x-auto rounded-2xl border border-line bg-panel">
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img"
        aria-label="Workflow graph of subtasks and the agents assigned to them" className="mx-auto block">
        {nodes.flatMap((n) =>
          (n.depends_on || []).filter((d) => pos[d]).map((d) => {
            const a = pos[d], b = pos[n.id]
            const x1 = a.x + W, y1 = a.y + H / 2, x2 = b.x, y2 = b.y + H / 2
            const mx = (x1 + x2) / 2
            const live = n.status === 'running'
            return (
              <path key={`${d}-${n.id}`} d={`M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`}
                fill="none" stroke={live ? agentColor(n.agent_id) : '#b9c5be'} strokeWidth={live ? 2.5 : 1.5}
                className={live ? 'edge-live' : ''} />
            )
          })
        )}
        {nodes.map((n) => {
          const { x, y } = pos[n.id]
          const chosenId = n.agent_id || state.selections[n.id]?.chosen?.id
          const chosenName = n.agent_name || state.selections[n.id]?.chosen?.name || ''
          const color = agentColor(chosenId)
          const st = n.status
          const stroke = st === 'failed' ? '#c0392b' : st === 'skipped' || st === 'pending' ? '#9aa8a0' : color
          const fill = st === 'done' ? color : st === 'running' ? color : '#ffffff'
          const fillOp = st === 'done' ? 0.12 : st === 'running' ? 0.08 : 1
          return (
            <g key={n.id} transform={`translate(${x},${y})`} className={st === 'running' ? 'node-live' : ''}>
              <title>{n.instruction}</title>
              <rect width={W} height={H} rx="14" fill={fill} fillOpacity={fillOp} stroke={stroke}
                strokeWidth={st === 'running' ? 2.5 : 1.5} strokeDasharray={st === 'pending' || st === 'skipped' ? '5 4' : undefined} />
              <rect x="0" y="0" width="6" height={H} rx="3" fill={color} opacity={st === 'skipped' ? 0.3 : 1} />
              <text x="20" y="28" fontSize="14" fontWeight="600" fill="#15221d" fontFamily="Bricolage Grotesque, sans-serif">
                {clip(n.title, 24)}
              </text>
              <text x="20" y="48" fontSize="12" fill="#5c6b64">{clip(chosenName, 26)}</text>
              <text x="20" y="64" fontSize="11" fill={st === 'failed' ? '#c0392b' : '#5c6b64'}>
                {st === 'pending' && 'Waiting'}
                {st === 'running' && `Running${n.attempt > 1 ? `, attempt ${n.attempt}` : ''}`}
                {st === 'done' && `Done, score ${(n.score ?? 0).toFixed(2)}`}
                {st === 'skipped' && 'Skipped'}
                {st === 'failed' && 'Failed'}
              </text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}
