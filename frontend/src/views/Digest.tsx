import { useState, useEffect } from 'react'
import { getDigest, runDigest } from '../lib/api'
import Markdown from '../components/Markdown'

export default function Digest() {
  const [content, setContent] = useState<string>('')
  const [generatedAt, setGeneratedAt] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    getDigest().then(d => {
      if (d.content) setContent(d.content)
      setGeneratedAt(d.generated_at)
    })
  }, [])

  async function refresh() {
    setLoading(true)
    try {
      const d = await runDigest()
      if (d.content) setContent(d.content)
      setGeneratedAt(d.generated_at)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-[#d4a017] font-bold text-sm">Morning Briefing</h1>
          {generatedAt && (
            <p className="text-[#555] text-xs mt-0.5">
              {new Date(generatedAt).toLocaleString()}
            </p>
          )}
        </div>
        <button
          className="text-xs bg-[#1e1e1e] px-3 py-1.5 rounded hover:bg-[#2a2a2a] disabled:opacity-40"
          onClick={refresh}
          disabled={loading}
        >
          {loading ? 'running...' : '↻ refresh'}
        </button>
      </div>
      {content ? (
        <Markdown className="prose prose-invert prose-sm max-w-none text-xs">{content}</Markdown>
      ) : (
        <p className="text-[#555] text-xs">
          {loading ? 'Generating digest...' : 'Click ↻ refresh to generate your morning briefing'}
        </p>
      )}
    </div>
  )
}
