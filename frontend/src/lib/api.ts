const BASE = '/api'

export async function postChat(query: string, sessionId?: string) {
  const r = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, session_id: sessionId }),
  })
  return r.json()
}

export function streamChat(query: string, onToken: (t: string) => void, onDone: () => void) {
  const url = `${BASE}/chat/stream?query=${encodeURIComponent(query)}`
  const es = new EventSource(url)
  es.onmessage = (e) => {
    if (e.data === '[DONE]') { onDone(); es.close(); return }
    onToken(e.data)
  }
  return es
}

export async function getStatus() {
  return (await fetch(`${BASE}/status`)).json()
}

export async function getDigest(): Promise<{ content: string; generated_at: string | null }> {
  return (await fetch(`${BASE}/digest`)).json()
}

export async function runDigest(): Promise<{ content: string; generated_at: string | null }> {
  return (await fetch(`${BASE}/digest/run`, { method: 'POST' })).json()
}

export async function getConfig(): Promise<{
  user: { name: string; timezone: string; role: string }
  llm: { provider: string; model: string }
  connectors: Record<string, boolean>
}> {
  return (await fetch(`${BASE}/config`)).json()
}

export async function getNotionTree() {
  return (await fetch(`${BASE}/notion/tree`)).json()
}

export async function getNotionPage(pageId: string) {
  return (await fetch(`${BASE}/notion/page?page_id=${pageId}`)).json()
}

export async function searchNotion(q: string) {
  return (await fetch(`${BASE}/notion/search?q=${encodeURIComponent(q)}`)).json()
}
