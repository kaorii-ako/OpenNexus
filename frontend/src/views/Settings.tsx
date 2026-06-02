import { useState, useEffect } from 'react'
import { getConfig } from '../lib/api'

export default function Settings() {
  const [cfg, setCfg] = useState<{
    user: { name: string; timezone: string; role: string }
    llm: { provider: string; model: string }
    connectors: Record<string, boolean>
  } | null>(null)

  useEffect(() => { getConfig().then(setCfg).catch(() => {}) }, [])

  if (!cfg) return <div className="p-6 text-[#444] text-xs">Loading...</div>

  return (
    <div className="p-6 max-w-2xl space-y-6">
      <h1 className="text-[#d4a017] font-bold text-sm tracking-widest uppercase">Settings</h1>

      <section>
        <h2 className="text-xs text-[#555] uppercase tracking-widest mb-2">Identity</h2>
        <div className="bg-[#0f0f0f] border border-[#1e1e1e] rounded p-4 space-y-2">
          <Row label="Name" value={cfg.user.name} />
          <Row label="Timezone" value={cfg.user.timezone} />
          <Row label="Role" value={cfg.user.role || '—'} />
        </div>
      </section>

      <section>
        <h2 className="text-xs text-[#555] uppercase tracking-widest mb-2">LLM</h2>
        <div className="bg-[#0f0f0f] border border-[#1e1e1e] rounded p-4 space-y-2">
          <Row label="Provider" value={cfg.llm.provider} />
          <Row label="Model" value={cfg.llm.model} />
        </div>
      </section>

      <section>
        <h2 className="text-xs text-[#555] uppercase tracking-widest mb-2">Connectors</h2>
        <div className="bg-[#0f0f0f] border border-[#1e1e1e] rounded p-4 space-y-2">
          {Object.entries(cfg.connectors).map(([name, enabled]) => (
            <div key={name} className="flex items-center justify-between">
              <span className="text-xs text-[#e0e0e0] font-mono">{name}</span>
              <span className={`text-xs ${enabled ? 'text-green-500' : 'text-[#333]'}`}>
                {enabled ? 'enabled' : 'disabled'}
              </span>
            </div>
          ))}
        </div>
      </section>

      <p className="text-[#333] text-xs">
        Edit <span className="font-mono text-[#555]">nexus.toml</span> to change settings,
        or run <span className="font-mono text-[#555]">nexus init</span> to reconfigure.
      </p>
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs text-[#555]">{label}</span>
      <span className="text-xs text-[#e0e0e0] font-mono">{value}</span>
    </div>
  )
}
