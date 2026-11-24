import { usd } from '../theme'

function Bar({ label, used, limit, fmt }) {
  const pct = Math.min(100, (used / limit) * 100)
  const over = used > limit
  return (
    <div>
      <div className="mb-1 flex justify-between text-sm">
        <span className="font-medium">{label}</span>
        <span className={`tabular-nums ${over ? 'font-semibold text-bad' : 'text-muted'}`}>{fmt(used)} of {fmt(limit)}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-paper">
        <div className={`h-full rounded-full transition-all duration-500 ${over ? 'bg-bad' : 'bg-signal'}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

function Stat({ label, value }) {
  return (
    <div className="rounded-xl bg-paper px-3 py-2">
      <div className="text-xs text-muted">{label}</div>
      <div className="font-display text-lg font-semibold tabular-nums">{value}</div>
    </div>
  )
}

export default function Metrics({ state }) {
  const m = state.final?.metrics
  const meta = state.meta
  const cost = m ? m.cost_usd : state.live.cost
  const time = m ? m.total_latency_s : state.lastT
  const count = (a) => state.adapts.filter((x) => x.action === a).length
  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-line bg-panel p-5">
      <h3 className="text-lg font-semibold">Resources</h3>
      {meta && (
        <>
          <Bar label="Cost" used={cost} limit={meta.budget_usd} fmt={usd} />
          <Bar label="Time" used={time} limit={meta.budget_s} fmt={(v) => `${v.toFixed(1)}s`} />
        </>
      )}
      <div className="grid grid-cols-2 gap-2">
        <Stat label="Agent calls" value={m ? m.agent_calls : state.live.calls} />
        <Stat label="Tokens" value={(m ? m.tokens_in + m.tokens_out : state.live.tokens_in + state.live.tokens_out).toLocaleString()} />
        <Stat label="Retries" value={m ? m.retries : count('retry')} />
        <Stat label="Agent swaps" value={m ? m.replacements : count('replace')} />
        <Stat label="Steps skipped" value={m ? m.skipped_steps : count('skip') + count('early_stop') + count('stop')} />
        <Stat label="Topology" value={state.topology?.topology ?? '-'} />
      </div>
      {m && (
        <div className="grid grid-cols-2 gap-2 border-t border-line pt-4">
          <Stat label="Judge quality" value={m.judge_quality != null ? `${(m.judge_quality * 10).toFixed(0)}/10` : 'n/a'} />
          <Stat label="Heuristic quality" value={m.heuristic_quality.toFixed(2)} />
          <div className={`col-span-2 rounded-xl px-3 py-2 text-sm font-medium ${m.budget_ok ? 'bg-signal-soft text-signal' : 'bg-red-100 text-bad'}`}>
            {m.budget_ok ? 'Finished within both budgets' : 'Exceeded a budget'}
          </div>
        </div>
      )}
    </div>
  )
}
