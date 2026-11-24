import { useEffect, useState } from 'react'
import { listRuns } from '../api'
import { strategyLabel, usd } from '../theme'

export default function History({ onOpen }) {
  const [runs, setRuns] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => { listRuns().then(setRuns).catch((e) => setError(e.message)) }, [])

  if (error) return <p className="rounded-xl bg-red-100 p-3 text-sm text-bad">{error}</p>
  if (!runs) return <p className="text-muted">Loading...</p>
  if (!runs.length) return <p className="text-muted">No runs yet. Run a task and it will be saved here.</p>

  return (
    <div className="overflow-x-auto rounded-2xl border border-line bg-panel">
      <table className="w-full min-w-[640px] text-left text-sm tabular-nums">
        <thead className="border-b border-line text-muted">
          <tr><th className="p-3 font-medium">Task</th><th className="p-3 font-medium">Strategy</th>
            <th className="p-3 font-medium">Time</th><th className="p-3 font-medium">Cost</th>
            <th className="p-3 font-medium">Quality</th><th className="p-3 font-medium">Status</th></tr>
        </thead>
        <tbody>
          {runs.map((r) => (
            <tr key={r.id} onClick={() => onOpen(r.id)} className="cursor-pointer border-b border-line/60 hover:bg-paper">
              <td className="max-w-xs truncate p-3">{r.task}</td>
              <td className="p-3">{strategyLabel(r.strategy)}</td>
              <td className="p-3">{r.metrics.total_latency_s != null ? `${r.metrics.total_latency_s}s` : '-'}</td>
              <td className="p-3">{r.metrics.cost_usd != null ? usd(r.metrics.cost_usd) : '-'}</td>
              <td className="p-3">{r.metrics.judge_quality != null ? `${(r.metrics.judge_quality * 10).toFixed(0)}/10` : '-'}</td>
              <td className="p-3">{r.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
