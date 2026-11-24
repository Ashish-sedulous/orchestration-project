import { useEffect, useReducer } from 'react'
import { reducer, initialState } from './reducer'
import { API } from './theme'

export function useRun(runId) {
  const [state, dispatch] = useReducer(reducer, initialState)
  useEffect(() => {
    dispatch({ type: 'reset' })
    if (!runId) return undefined
    const es = new EventSource(`${API}/api/runs/${runId}/events`)
    es.onmessage = (m) => dispatch({ type: 'event', e: JSON.parse(m.data) })
    es.addEventListener('end', () => es.close())
    es.onerror = () => es.close()
    return () => es.close()
  }, [runId])
  return state
}
