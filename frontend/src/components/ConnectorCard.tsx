interface ConnectorCardProps {
  name: string
  enabled: boolean
  healthy: boolean | null
  lastSync?: string | null
  error?: string | null
}

export default function ConnectorCard({ name, enabled, healthy, lastSync, error }: ConnectorCardProps) {
  const dot = !enabled
    ? <span className="text-[#333]">●</span>
    : healthy === null
    ? <span className="text-[#555] animate-pulse">●</span>
    : healthy
    ? <span className="text-green-500">●</span>
    : <span className="text-red-500">●</span>

  const label = !enabled ? 'disabled' : healthy === null ? 'checking...' : healthy ? 'connected' : 'error'
  const labelColor = !enabled ? 'text-[#333]' : healthy ? 'text-green-600' : 'text-red-600'

  return (
    <div className="bg-[#0f0f0f] border border-[#1e1e1e] rounded p-3 flex flex-col gap-1">
      <div className="flex items-center gap-2">
        {dot}
        <span className="text-xs font-mono text-[#e0e0e0]">{name}</span>
        <span className={`text-xs ml-auto ${labelColor}`}>{label}</span>
      </div>
      {lastSync && (
        <span className="text-[#333] text-xs">synced {new Date(lastSync).toLocaleTimeString()}</span>
      )}
      {error && <span className="text-red-900 text-xs truncate">{error}</span>}
    </div>
  )
}
