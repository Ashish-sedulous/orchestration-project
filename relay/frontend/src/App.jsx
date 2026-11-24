import { useEffect, useState } from 'react'
import { getHealth, startRun } from './api'
import { useRun } from './useRun'
import TaskForm from './components/TaskForm'
import RunView from './components/RunView'
import Compare from './components/Compare'
import History from './components/History'
import AgentsPanel from './components/AgentsPanel'

const TABS = [
  { id: 'run', label: 'Run' },
  { id: 'compare', label: 'Compare' },
  { id: 'history', label: 'History' },
  { id: 'agents', label: 'Agents' },
]

export default function App() {
  const [tab, setTab] = useState('run')
  const [runId, setRunId] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [online, setOnline] = useState(null)
  const state = useRun(runId)

  useEffect(() => { getHealth().then(() => setOnline(true)).catch(() => setOnline(false)) }, [])

  const run = async (form) => {
    setError(''); setBusy(true)
    try { setRunId((await startRun(form)).run_id) } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  const open = (id) => { setRunId(id); setTab('run') }
  const running = busy || state.status === 'running'

  return (
    <div className="mx-auto max-w-[1400px] px-5 pb-16 pt-6">
      <header className="mb-6 flex flex-wrap items-center gap-x-8 gap-y-3">
        <div>
          <h1 className="text-3xl font-bold">Relay</h1>
          <p className="text-sm text-muted">Adaptive multi-agent orchestration</p>
        </div>
        <nav className="flex gap-1 rounded-xl bg-panel p-1 shadow-sm" aria-label="Sections">
          {TABS.map((t) => (
            <button key={t.id} onClick={() => setTab(t.id)} aria-current={tab === t.id ? 'page' : undefined}
              className={`rounded-lg px-4 py-1.5 text-sm font-medium transition-colors ${tab === t.id ? 'bg-signal text-white' : 'text-muted hover:text-ink'}`}>
              {t.label}
            </button>
          ))}
        </nav>
        <span className={`ml-auto rounded-full px-3 py-1 text-xs font-medium ${online === false ? 'bg-red-100 text-bad' : 'bg-panel text-muted'}`}>
          {online === null ? 'Connecting...' : online ? 'Backend connected' : 'Backend offline: start the API on port 8000'}
        </span>
      </header>

      {tab === 'run' && (
        <div className="grid gap-6 lg:grid-cols-[340px_minmax(0,1fr)]">
          <div className="lg:sticky lg:top-6 lg:self-start">
            <TaskForm onSubmit={run} busy={running} />
            {error && <p className="mt-3 rounded-xl bg-red-100 p-3 text-sm text-bad">{error}</p>}
          </div>
          <RunView state={state} />
        </div>
      )}
      {tab === 'compare' && <Compare />}
      {tab === 'history' && <History onOpen={open} />}
      {tab === 'agents' && <AgentsPanel />}
    </div>
  )
}
