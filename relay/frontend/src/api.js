import { API } from './theme'

async function json(res) {
  if (!res.ok) {
    let detail = res.statusText
    try { detail = JSON.stringify((await res.json()).detail ?? detail) } catch { /* ignore */ }
    throw new Error(`Request failed: ${detail}`)
  }
  return res.json()
}

export const startRun = (body) =>
  fetch(`${API}/api/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then(json)

export const listRuns = () => fetch(`${API}/api/runs`).then(json)
export const listAgents = () => fetch(`${API}/api/agents`).then(json)
export const getHealth = () => fetch(`${API}/api/health`).then(json)
