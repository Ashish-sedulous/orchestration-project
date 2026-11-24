export const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const COLORS = {
  research_fast: '#2f6be0',
  research_deep: '#1f4fb5',
  analyst: '#b7791f',
  coder_fast: '#8b5cf6',
  coder_deep: '#6d3fc4',
  critic: '#cf4067',
  generalist: '#55606a',
}
export const agentColor = (id) => COLORS[id] || '#55606a'

export const usd = (n) =>
  n == null ? '-' : n < 0.01 ? `$${n.toFixed(5)}` : `$${n.toFixed(3)}`

export const STRATEGIES = [
  { id: 'adaptive', label: 'Adaptive', hint: 'Plans the task, picks agents, adapts as it runs' },
  { id: 'single', label: 'Single agent', hint: 'One strong model call, no orchestration' },
  { id: 'fixed_pipeline', label: 'Fixed pipeline', hint: 'Research, analyze and review every time' },
]
export const strategyLabel = (id) => STRATEGIES.find((s) => s.id === id)?.label || id

export const EXAMPLES = [
  'Compare the pros and cons of PostgreSQL and MongoDB for a startup building a social app, then recommend one.',
  'Write a Python function that merges overlapping intervals, and explain its time complexity.',
  'What is the capital of Australia?',
]
