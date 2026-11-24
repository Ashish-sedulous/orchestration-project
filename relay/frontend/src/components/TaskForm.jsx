import { useState } from 'react'
import { EXAMPLES, STRATEGIES } from '../theme'

const PRIORITIES = [
  { id: 'quality', label: 'Quality' },
  { id: 'balanced', label: 'Balanced' },
  { id: 'economy', label: 'Economy' },
]

function Segmented({ value, onChange, options, label }) {
  return (
    <div role="radiogroup" aria-label={label} className="grid auto-cols-fr grid-flow-col gap-1 rounded-xl bg-paper p-1">
      {options.map((o) => (
        <button
          key={o.id} type="button" role="radio" aria-checked={value === o.id}
          onClick={() => onChange(o.id)}
          className={`rounded-lg px-2 py-1.5 text-sm font-medium transition-colors ${
            value === o.id ? 'bg-panel text-ink shadow-sm' : 'text-muted hover:text-ink'
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}

export default function TaskForm({ onSubmit, busy, showStrategy = true, submitLabel = 'Run task' }) {
  const [task, setTask] = useState('')
  const [strategy, setStrategy] = useState('adaptive')
  const [priority, setPriority] = useState('balanced')
  const [budgetUsd, setBudgetUsd] = useState(0.02)
  const [budgetS, setBudgetS] = useState(90)
  const [judge, setJudge] = useState(true)

  const submit = (e) => {
    e.preventDefault()
    if (task.trim().length < 3 || busy) return
    onSubmit({ task: task.trim(), strategy, priority, budget_usd: budgetUsd, budget_s: budgetS, judge })
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-5 rounded-2xl border border-line bg-panel p-5">
      <div>
        <label htmlFor="task" className="mb-1.5 block text-sm font-semibold">What should the agents do?</label>
        <textarea
          id="task" value={task} onChange={(e) => setTask(e.target.value)} rows={5} maxLength={4000}
          placeholder="Describe a task, for example a comparison, a coding job or a research question."
          className="w-full resize-y rounded-xl border border-line bg-white p-3 text-[15px] leading-relaxed placeholder:text-muted/70"
        />
        <div className="mt-2 flex flex-wrap gap-1.5">
          {EXAMPLES.map((ex, i) => (
            <button key={i} type="button" onClick={() => setTask(ex)}
              className="rounded-full border border-line px-2.5 py-1 text-xs text-muted transition-colors hover:border-signal hover:text-signal">
              Example {i + 1}
            </button>
          ))}
        </div>
      </div>

      {showStrategy && (
        <div>
          <div className="mb-1.5 text-sm font-semibold">Strategy</div>
          <Segmented value={strategy} onChange={setStrategy} options={STRATEGIES} label="Strategy" />
          <p className="mt-1.5 text-xs text-muted">{STRATEGIES.find((s) => s.id === strategy)?.hint}</p>
        </div>
      )}

      <div>
        <div className="mb-1.5 text-sm font-semibold">Priority</div>
        <Segmented value={priority} onChange={setPriority} options={PRIORITIES} label="Priority" />
        <p className="mt-1.5 text-xs text-muted">Shifts how the selector trades quality against cost and speed.</p>
      </div>

      <div className="grid gap-4">
        <label className="block text-sm">
          <span className="flex justify-between font-semibold">Cost budget <span className="font-normal tabular-nums text-muted">${budgetUsd.toFixed(3)}</span></span>
          <input type="range" min="0.002" max="0.05" step="0.001" value={budgetUsd}
            onChange={(e) => setBudgetUsd(+e.target.value)} className="mt-1 w-full accent-signal" />
        </label>
        <label className="block text-sm">
          <span className="flex justify-between font-semibold">Time budget <span className="font-normal tabular-nums text-muted">{budgetS}s</span></span>
          <input type="range" min="10" max="180" step="5" value={budgetS}
            onChange={(e) => setBudgetS(+e.target.value)} className="mt-1 w-full accent-signal" />
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={judge} onChange={(e) => setJudge(e.target.checked)} className="accent-signal" />
          Score the final answer with an LLM judge
        </label>
      </div>

      <button type="submit" disabled={busy || task.trim().length < 3}
        className="rounded-xl bg-signal px-4 py-2.5 font-semibold text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40">
        {busy ? 'Running...' : submitLabel}
      </button>
    </form>
  )
}
