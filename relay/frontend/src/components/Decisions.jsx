import { agentColor } from '../theme'

const ACTION_LABEL = {
  retry: 'Retried', replace: 'Swapped agent', skip: 'Skipped', early_stop: 'Stopped early',
  stop: 'Stopped', downgrade: 'Downgraded model',
}

export default function Decisions({ state }) {
  const sels = state.order.map((id) => state.selections[id]).filter(Boolean)
  return (
    <div className="flex flex-col gap-5 rounded-2xl border border-line bg-panel p-5">
      <h3 className="text-lg font-semibold">Why this plan</h3>

      {state.topology && (
        <p className="text-[15px] leading-relaxed">
          <span className="font-semibold capitalize">{state.topology.topology} workflow.</span>{' '}
          {state.topology.reason}
        </p>
      )}

      <div className="flex flex-col gap-3">
        {sels.map((s) => (
          <details key={s.node_id} className="group rounded-xl border border-line">
            <summary className="flex cursor-pointer items-center gap-2 px-3 py-2.5 text-sm">
              <span className="h-3 w-3 shrink-0 rounded-full" style={{ background: agentColor(s.chosen.id) }} />
              <span className="font-medium">{state.nodes[s.node_id]?.title}</span>
              <span className="text-muted">assigned to {s.chosen.name}</span>
            </summary>
            <div className="border-t border-line px-3 py-3 text-sm">
              <p className="mb-2 leading-relaxed text-muted">{s.rationale}</p>
              {s.ranking.length > 0 && (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs tabular-nums">
                    <thead className="text-muted">
                      <tr><th className="py-1 pr-3 font-medium">Agent</th><th className="pr-3 font-medium">Match</th>
                        <th className="pr-3 font-medium">Quality</th><th className="pr-3 font-medium">Reliab.</th>
                        <th className="pr-3 font-medium">Cost</th><th className="pr-3 font-medium">Score</th></tr>
                    </thead>
                    <tbody>
                      {s.ranking.map((r, i) => (
                        <tr key={r.id} className={i === 0 ? 'font-semibold' : 'text-muted'}>
                          <td className="py-1 pr-3">{r.name}{!r.feasible && ' (over budget)'}</td>
                          <td className="pr-3">{Math.round(r.cm * 100)}%</td><td className="pr-3">{r.q.toFixed(2)}</td>
                          <td className="pr-3">{r.r.toFixed(2)}</td><td className="pr-3">${r.cost.toFixed(5)}</td>
                          <td className="pr-3">{r.score.toFixed(3)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </details>
        ))}
        {!sels.length && <p className="text-sm text-muted">Agent choices and their scores appear here.</p>}
      </div>

      {state.adapts.length > 0 && (
        <div>
          <h4 className="mb-2 text-sm font-semibold">Adaptations during the run</h4>
          <ul className="flex flex-col gap-2">
            {state.adapts.map((a, i) => (
              <li key={i} className="rounded-xl bg-paper px-3 py-2 text-sm leading-relaxed">
                <span className="font-semibold">{ACTION_LABEL[a.action] || a.action}.</span>{' '}
                <span className="text-muted">{a.reason}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
