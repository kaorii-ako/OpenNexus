import { useEffect, useState } from 'react'
import { getStatus } from '../lib/api'

interface ConnectorStatus { name: string; healthy: boolean; error?: string }

export default function Status() {
  const [data, setData] = useState<{ connectors: ConnectorStatus[]; model: string } | null>(null)

  useEffect(() => { getStatus().then(setData) }, [])

  return (
    <div className="p-6">
      <h1 className="text-[#d4a017] font-bold text-sm mb-4">System Status</h1>
      {data ? (
        <>
          <p className="text-xs text-[#555] mb-4">Model: <span className="text-[#e0e0e0]">{data.model}</span></p>
          <div className="space-y-2">
            {data.connectors.map(c => (
              <div key={c.name} className="flex items-center gap-3 text-xs">
                <span className={c.healthy ? 'text-green-500' : 'text-red-500'}>
                  {c.healthy ? '●' : '○'}
                </span>
                <span className="text-[#e0e0e0] w-24">{c.name}</span>
                {c.error && <span className="text-[#555]">{c.error}</span>}
              </div>
            ))}
          </div>
        </>
      ) : (
        <p className="text-[#555] text-xs">Loading...</p>
      )}
    </div>
  )
}
