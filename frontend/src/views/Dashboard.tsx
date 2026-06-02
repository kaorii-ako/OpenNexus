import { useState, useEffect } from 'react'
import { getDigest, runDigest, getConfig, getStatus } from '../lib/api'
import Markdown from '../components/Markdown'
import ConnectorCard from '../components/ConnectorCard'
import { useNavigate } from 'react-router-dom'

interface ConnectorStatus { name: string; healthy: boolean; error?: string }

export default function Dashboard() {
  const navigate = useNavigate()
  const [userName, setUserName] = useState('there')
  const [digest, setDigest] = useState<{ content: string; generated_at: string | null } | null>(null)
  const [connectors, setConnectors] = useState<ConnectorStatus[]>([])
  const [enabledMap, setEnabledMap] = useState<Record<string, boolean>>({})
  const [running, setRunning] = useState(false)

  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'

  useEffect(() => {
    getConfig().then(cfg => {
      setUserName(cfg.user.name)
      setEnabledMap(cfg.connectors)
    }).catch(() => {})
    getDigest().then(d => setDigest(d)).catch(() => {})
    getStatus().then(s => setConnectors(s.connectors || [])).catch(() => {})
  }, [])

  async function runBriefing() {
    setRunning(true)
    try {
      const d = await runDigest()
      setDigest(d)
    } finally {
      setRunning(false)
    }
  }

  const connectorNames = ['notion', 'gmail', 'calendar', 'classroom', 'github', 'discord']

  return (
    <div className="p-6 max-w-4xl space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-lg font-bold text-[#e0e0e0]">
          {greeting}, <span className="text-[#d4a017]">{userName}</span>
        </h1>
        <p className="text-[#444] text-xs mt-0.5">
          {new Date().toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
        </p>
      </div>

      {/* Quick actions */}
      <div className="flex gap-2 flex-wrap">
        <button
          onClick={() => navigate('/chat')}
          className="text-xs bg-[#d4a017] text-black px-3 py-1.5 rounded font-bold hover:bg-[#c49015]"
        >
          Ask NEXUS
        </button>
        <button
          onClick={runBriefing}
          disabled={running}
          className="text-xs bg-[#1e1e1e] border border-[#2a2a2a] px-3 py-1.5 rounded hover:bg-[#2a2a2a] disabled:opacity-40"
        >
          {running ? 'Running...' : '↻ Run Briefing'}
        </button>
      </div>

      {/* Digest card */}
      <div className="bg-[#0f0f0f] border border-[#1e1e1e] rounded p-4">
        <div className="flex items-center justify-between mb-3">
          <span className="text-[#d4a017] text-xs font-bold">Morning Briefing</span>
          {digest?.generated_at && (
            <span className="text-[#333] text-xs">{new Date(digest.generated_at).toLocaleString()}</span>
          )}
        </div>
        {digest?.content ? (
          <div className="max-h-80 overflow-auto">
            <Markdown className="prose prose-invert prose-xs max-w-none text-xs">{digest.content}</Markdown>
          </div>
        ) : (
          <p className="text-[#444] text-xs">{running ? 'Generating...' : 'No briefing yet — click ↻ Run Briefing'}</p>
        )}
      </div>

      {/* Connector grid */}
      <div>
        <h2 className="text-xs text-[#555] mb-2 uppercase tracking-widest">Connectors</h2>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {connectorNames.map(name => {
            const status = connectors.find(c => c.name === name)
            return (
              <ConnectorCard
                key={name}
                name={name}
                enabled={enabledMap[name] ?? false}
                healthy={status ? status.healthy : null}
                error={status?.error}
              />
            )
          })}
        </div>
      </div>
    </div>
  )
}
