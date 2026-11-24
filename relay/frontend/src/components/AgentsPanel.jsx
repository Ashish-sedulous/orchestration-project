import { useEffect, useState } from 'react'
import { listAgents } from '../api'
import { agentColor, usd } from '../theme'

export default function AgentsPanel() {
  const [agents, setAgents] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => { listAgents().then(setAgents).catch((e) => setError(e.message)) }, [])

  if (error) return <p className="rounded-xl bg-red-100 p-3 text-sm text-bad">{error}</p>
  if (!agents) return <p className="text-muted">Loading...</p>

  return (
    <div className="flex flex-col gap-4">
      <p className="max-w-2xl text-sm text-muted">
        These estimates start as priors and move toward observed behaviour as agents complete steps
        (shrinkage: a few observations nudge the estimate, many dominate it). Run a few tasks and refresh.
      </p>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {agents.map((a) => (
          <div key={a.id} className="rounded-2xl border border-line bg-panel p-4">
            <div className="flex items-center gap-2">
              <span className="h-3.5 w-3.5 rounded-full" style={{ background: agentColor(a.id) }} />
              <h3 className="font-semibold">{a.name}</h3>
              <span className="ml-auto rounded-full bg-paper px-2 py-0.5 text-xs text-muted">{a.tier}</span>
            </div>
            <p className="mt-2 text-sm text-muted">{a.description}</p>
            <p className="mt-2 text-xs text-muted">Model: {a.model}</p>
            <div className="mt-2 flex flex-wrap gap-1">
              {a.capabilities.map((c) => <span key={c} className="rounded-full bg-signal-soft px-2 py-0.5 text-xs text-signal">{c}</span>)}
            </div>
            <dl className="mt-3 grid grid-cols-3 gap-2 text-xs tabular-nums">
              <div><dt className="text-muted">Quality</dt><dd className="font-semibold">{a.est_quality}</dd></div>
              <div><dt className="text-muted">Success</dt><dd className="font-semibold">{a.est_success}</dd></div>
              <div><dt className="text-muted">Latency</dt><dd className="font-semibold">{a.est_latency_s}s</dd></div>
              <div><dt className="text-muted">Cost</dt><dd className="font-semibold">{usd(a.est_cost)}</dd></div>
              <div><dt className="text-muted">Calls</dt><dd className="font-semibold">{a.calls}</dd></div>
              <div><dt className="text-muted">Observed</dt><dd className="font-semibold">{a.observations}</dd></div>
            </dl>
          </div>
        ))}
      </div>
    </div>
  )
}
