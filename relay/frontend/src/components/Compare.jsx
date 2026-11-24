import { useState } from 'react'
import { startRun } from '../api'
import { useRun } from '../useRun'
import { STRATEGIES, usd } from '../theme'
import TaskForm from './TaskForm'

const ROWS = [
  { key: 'total_latency_s', label: 'Total time', fmt: (v) => `${v.toFixed(1)}s`, best: 'min' },
  { key: 'cost_usd', label: 'Cost', fmt: usd, best: 'min' },
  { key: 'agent_calls', label: 'Agent calls', fmt: (v) => v, best: 'min' },
  { key: 'tokens', label: 'Tokens', fmt: (v) => v.toLocaleString(), best: 'min' },
  { key: 'judge_quality', label: 'Judge quality', fmt: (v) => `${(v * 10).toFixed(0)}/10`, best: 'max' },
  { key: 'heuristic_quality', label: 'Heuristic quality', fmt: (v) => v.toFixed(2), best: 'max' },
  { key: 'budget_ok', label: 'Within budgets', fmt: (v) => (v ? 'Yes' : 'No'), best: null },
]

const val = (state, key) => {
  const m = state.final?.metrics
  if (!m) return null
  return key === 'tokens' ? m.tokens_in + m.tokens_out : m[key]
}

export default function Compare() {
  const [ids, setIds] = useState([null, null, null])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const s0 = useRun(ids[0])
  const s1 = useRun(ids[1])
  const s2 = useRun(ids[2])
  const states = [s0, s1, s2]
  const running = busy || states.some((s) => s.status === 'running')

  const go = async (form) => {
    setError(''); setBusy(true)
    try {
      const res = await Promise.all(STRATEGIES.map((s) => startRun({ ...form, strategy: s.id })))
      setIds(res.map((r) => r.run_id))
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  const bestIdx = (row) => {
    if (!row.best) return -1
    const vals = states.map((s) => val(s, row.key))
    if (vals.some((v) => v == null)) return -1
    const target = row.best === 'min' ? Math.min(...vals) : Math.max(...vals)
    return vals.indexOf(target)
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[340px_minmax(0,1fr)]">
      <div className="lg:sticky lg:top-6 lg:self-start">
        <TaskForm onSubmit={go} busy={running} showStrategy={false} submitLabel="Compare all three" />
        {error && <p className="mt-3 rounded-xl bg-red-100 p-3 text-sm text-bad">{error}</p>}
      </div>
      <div className="flex flex-col gap-5">
        <div className="rounded-2xl border border-line bg-panel p-5">
          <h2 className="mb-1 text-xl font-semibold">Same task, three strategies</h2>
          <p className="mb-4 text-sm text-muted">Runs adaptive, single-agent and fixed-pipeline side by side. Highlighted cells are the best value in each row.</p>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[480px] text-left text-sm tabular-nums">
              <thead>
                <tr className="border-b border-line">
                  <th className="py-2 pr-4 font-medium text-muted">Metric</th>
                  {STRATEGIES.map((s, i) => (
                    <th key={s.id} className="py-2 pr-4 font-semibold">
                      {s.label}
                      <span className="block text-xs font-normal text-muted">
                        {states[i].status === 'idle' ? '' : states[i].status === 'running' ? `running, ${states[i].lastT.toFixed(0)}s` : states[i].status}
                      </span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {ROWS.map((row) => {
                  const b = bestIdx(row)
                  return (
                    <tr key={row.key} className="border-b border-line/60">
                      <td className="py-2 pr-4 text-muted">{row.label}</td>
                      {states.map((s, i) => {
                        const v = val(s, row.key)
                        return (
                          <td key={i} className={`py-2 pr-4 ${b === i ? 'font-semibold text-signal' : ''}`}>
                            <span className={b === i ? 'rounded-md bg-signal-soft px-1.5 py-0.5' : ''}>{v == null ? '-' : row.fmt(v)}</span>
                          </td>
                        )
                      })}
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>

        <div className="grid gap-4 xl:grid-cols-3">
          {STRATEGIES.map((s, i) => (
            <div key={s.id} className="rounded-2xl border border-line bg-panel p-4">
              <h3 className="mb-2 font-semibold">{s.label}</h3>
              <div className="max-h-80 overflow-y-auto whitespace-pre-wrap text-sm leading-relaxed">
                {states[i].final?.answer ?? <span className="text-muted">{ids[i] ? 'Working...' : 'No run yet.'}</span>}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
