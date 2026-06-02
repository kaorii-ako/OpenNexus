import { useState, useRef, useEffect } from 'react'
import { streamChat } from '../lib/api'
import Markdown from '../components/Markdown'

interface SourceChip { page_title: string; heading?: string }
interface Message {
  role: 'user' | 'assistant'
  content: string
  sources?: SourceChip[]
}

function modeFromInput(input: string): string | null {
  if (input.startsWith('/code')) return 'code'
  if (input.startsWith('/think')) return 'think'
  return null
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const mode = modeFromInput(input)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  function send() {
    if (!input.trim() || streaming) return
    const query = input.trim()
    setInput('')
    setMessages(m => [...m, { role: 'user', content: query }])
    setMessages(m => [...m, { role: 'assistant', content: '', sources: [] }])
    setStreaming(true)
    streamChat(
      query,
      (token) => setMessages(m => {
        const copy = [...m]
        const last = copy[copy.length - 1]
        copy[copy.length - 1] = { ...last, content: last.content + token }
        return copy
      }),
      () => setStreaming(false),
    )
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-auto p-4 space-y-4">
        {messages.length === 0 && (
          <p className="text-[#333] text-xs text-center mt-16">
            Ask anything. Use <span className="text-[#555]">/code</span> or <span className="text-[#555]">/think</span> for specialised models.
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex flex-col gap-1 ${m.role === 'user' ? 'items-end' : 'items-start'}`}>
            <div
              className={`max-w-2xl px-3 py-2 rounded text-sm leading-relaxed ${
                m.role === 'user'
                  ? 'bg-[#1a1a1a] text-[#d4a017] border border-[#2a2a2a]'
                  : 'text-[#e0e0e0]'
              }`}
            >
              {m.role === 'assistant' ? (
                <Markdown>{m.content}</Markdown>
              ) : (
                m.content
              )}
              {streaming && i === messages.length - 1 && m.role === 'assistant' && (
                <span className="animate-pulse text-[#d4a017]">▋</span>
              )}
            </div>
            {m.sources && m.sources.length > 0 && (
              <div className="flex flex-wrap gap-1 px-1">
                {m.sources.map((s, j) => (
                  <span key={j} className="text-xs bg-[#111] border border-[#1e1e1e] rounded px-2 py-0.5 text-[#555]">
                    {s.page_title}{s.heading ? ` / ${s.heading}` : ''}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="border-t border-[#1a1a1a] p-3 space-y-2">
        {mode && (
          <div className="flex gap-1">
            <span className={`text-xs px-2 py-0.5 rounded border ${
              mode === 'code'
                ? 'border-blue-900 text-blue-400 bg-blue-950'
                : 'border-purple-900 text-purple-400 bg-purple-950'
            }`}>
              {mode} mode
            </span>
          </div>
        )}
        <div className="flex gap-2">
          <input
            ref={inputRef}
            className="flex-1 bg-[#0f0f0f] border border-[#1e1e1e] text-sm px-3 py-2 rounded text-[#e0e0e0] outline-none focus:border-[#d4a017] transition-colors"
            placeholder="/code · /think · or just ask..."
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send()}
          />
          <button
            className="bg-[#d4a017] text-black text-xs px-4 py-2 rounded font-bold disabled:opacity-40 hover:bg-[#c49015] transition-colors"
            onClick={send}
            disabled={streaming}
          >
            send
          </button>
        </div>
      </div>
    </div>
  )
}
