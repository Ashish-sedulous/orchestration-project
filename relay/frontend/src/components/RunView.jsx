import { strategyLabel } from '../theme'
import DagView from './DagView'
import Decisions from './Decisions'
import Metrics from './Metrics'
import { agentColor } from '../theme'

const STATUS = {
  idle: ['Ready', 'bg-paper text-muted'],
  running: ['Running', 'bg-signal-soft text-signal'],
  done: ['Complete', 'bg-signal-soft text-signal'],
  failed: ['Failed', 'bg-red-100 text-bad'],
}

export default function RunView({ state }) {
  const [label, cls] = STATUS[state.status] || STATUS.idle
  const outputs = state.order.map((id) => state.nodes[id]).filter((n) => n.output)

  if (state.status === 'idle') {
    return (
      <div className="flex min-h-[420px] flex-col items-center justify-center rounded-2xl border border-dashed border-line p-10 text-center">
        <h2 className="text-2xl font-semibold">Give the agents a task</h2>
        <p className="mt-2 max-w-md text-muted">
          Relay breaks the task into steps, chooses the cheapest agent that can do each one well,
          and shows every decision it makes. Try an example on the left.
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center gap-3">
        <span className={`rounded-full px-3 py-1 text-sm font-semibold ${cls}`}>{label}</span>
        {state.meta && <span className="text-sm text-muted">{strategyLabel(state.meta.strategy)}</span>}
        <span className="ml-auto text-sm tabular-nums text-muted">{state.lastT.toFixed(1)}s</span>
      </div>
      {state.meta && <p className="max-w-3xl text-[15px] leading-relaxed">{state.meta.task}</p>}

      <DagView state={state} />

      {state.error && <div className="rounded-xl bg-red-100 p-3 text-sm text-bad">{state.error}</div>}

      {state.final && (
        <section className="rounded-2xl border border-signal/40 bg-panel p-6">
          <h3 className="mb-3 text-xl font-semibold">Final answer</h3>
          <div className="max-w-3xl whitespace-pre-wrap text-[15px] leading-7">{state.final.answer}</div>
        </section>
      )}

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
        <Metrics state={state} />
        <Decisions state={state} />
      </div>

      {outputs.length > 0 && (
        <section className="rounded-2xl border border-line bg-panel p-5">
          <h3 className="mb-3 text-lg font-semibold">Intermediate outputs</h3>
          <div className="flex flex-col gap-2">
            {outputs.map((n) => (
              <details key={n.id} className="rounded-xl border border-line">
                <summary className="flex cursor-pointer items-center gap-2 px-3 py-2.5 text-sm">
                  <span className="h-3 w-3 rounded-full" style={{ background: agentColor(n.agent_id) }} />
                  <span className="font-medium">{n.title}</span>
                  <span className="text-muted">score {n.score?.toFixed(2)}</span>
                </summary>
                <div className="whitespace-pre-wrap border-t border-line px-3 py-3 text-sm leading-relaxed">{n.output}</div>
              </details>
            ))}
          </div>
        </section>
      )}

      <details className="rounded-2xl border border-line bg-panel p-5">
        <summary className="cursor-pointer text-lg font-semibold">Event log</summary>
        <ol className="mt-3 flex flex-col gap-1 text-sm">
          {state.log.map((l, i) => (
            <li key={i} className="flex gap-3"><span className="w-12 shrink-0 text-right tabular-nums text-muted">{l.t.toFixed(1)}s</span><span>{l.text}</span></li>
          ))}
        </ol>
      </details>
    </div>
  )
}
