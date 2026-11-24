// Turns the backend's event stream into UI state. The same reducer serves live runs and history.
export const initialState = {
  status: 'idle', meta: null, plan: null, nodes: {}, order: [], selections: {},
  topology: null, adapts: [], log: [], final: null, error: null, lastT: 0,
  live: { cost: 0, tokens_in: 0, tokens_out: 0, calls: 0 },
}

const addLog = (s, t, text) => [...s.log, { t, text }]
const patchNode = (s, id, patch) =>
  s.nodes[id] ? { ...s.nodes, [id]: { ...s.nodes[id], ...patch } } : s.nodes

export function reducer(s, action) {
  if (action.type === 'reset') return initialState
  const e = action.e
  const base = { ...s, lastT: e.t ?? s.lastT }
  switch (e.type) {
    case 'run_started':
      return { ...base, status: 'running', meta: e, log: addLog(s, e.t, 'Run started') }
    case 'plan':
      return {
        ...base, plan: e,
        nodes: Object.fromEntries(e.nodes.map((n) => [n.id, { ...n, status: 'pending' }])),
        order: e.nodes.map((n) => n.id),
        log: addLog(s, e.t, e.source === 'fixed'
          ? `Fixed workflow with ${e.nodes.length} step(s)`
          : `Planned ${e.nodes.length} subtask(s), ${e.category}, complexity ${e.complexity}`),
      }
    case 'selection':
      return { ...base, selections: { ...s.selections, [e.node_id]: e } }
    case 'topology':
      return { ...base, topology: e, log: addLog(s, e.t, `Topology: ${e.topology}. ${e.reason}`) }
    case 'node_start':
      return {
        ...base,
        nodes: patchNode(s, e.node_id, { status: 'running', agent_id: e.agent_id, agent_name: e.agent_name, tier: e.tier, attempt: e.attempt }),
        log: addLog(s, e.t, `${e.agent_name} started "${s.nodes[e.node_id]?.title}" (attempt ${e.attempt})`),
      }
    case 'attempt':
      return { ...base, log: addLog(s, e.t, e.ok ? `Attempt scored ${e.score.toFixed(2)}` : `Attempt failed: ${e.error}`) }
    case 'adapt':
      return { ...base, adapts: [...s.adapts, e], log: addLog(s, e.t, `Adaptation (${e.action}): ${e.reason}`) }
    case 'node_end':
      return {
        ...base,
        nodes: patchNode(s, e.node_id, { status: e.status, output: e.output, score: e.score, agent_id: e.agent_id || s.nodes[e.node_id]?.agent_id, note: e.note }),
        log: addLog(s, e.t, `"${s.nodes[e.node_id]?.title}" ${e.status}`),
      }
    case 'call':
      return {
        ...base,
        live: {
          cost: s.live.cost + e.cost, tokens_in: s.live.tokens_in + e.tokens_in,
          tokens_out: s.live.tokens_out + e.tokens_out, calls: s.live.calls + 1,
        },
      }
    case 'synthesis_start':
      return { ...base, log: addLog(s, e.t, `Combining results (${e.tier} model)`) }
    case 'final':
      return { ...base, status: 'done', final: e, log: addLog(s, e.t, 'Finished') }
    case 'error':
      return { ...base, status: 'failed', error: e.message, log: addLog(s, e.t, `Error: ${e.message}`) }
    default:
      return base
  }
}
