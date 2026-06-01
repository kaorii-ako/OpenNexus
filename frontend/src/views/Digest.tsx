import { useState } from 'react'
import { runDigest } from '../lib/api'
import Markdown from '../components/Markdown'

export default function Digest() {
  const [content, setContent] = useState<string>('')
  const [loading, setLoading] = useState(false)

  async function refresh() {
    setLoading(true)
    try {
      await runDigest()
      setContent('Digest triggered — check terminal for output.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-[#d4a017] font-bold text-sm">Morning Briefing</h1>
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
        <p className="text-[#555] text-xs">Click refresh to run the digest</p>
      )}
    </div>
  )
}
