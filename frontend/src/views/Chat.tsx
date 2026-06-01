import { useState, useRef, useEffect } from 'react'
import { streamChat } from '../lib/api'
import Markdown from '../components/Markdown'

interface Message { role: 'user' | 'assistant'; content: string }

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  function send() {
    if (!input.trim() || streaming) return
    const query = input.trim()
    setInput('')
    setMessages(m => [...m, { role: 'user', content: query }])
    setMessages(m => [...m, { role: 'assistant', content: '' }])
    setStreaming(true)
    streamChat(
      query,
      (token) => setMessages(m => {
        const copy = [...m]
        copy[copy.length - 1] = { ...copy[copy.length - 1], content: copy[copy.length - 1].content + token }
        return copy
      }),
      () => setStreaming(false),
    )
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-auto p-4 space-y-3">
        {messages.map((m, i) => (
          <div key={i} className={`text-xs leading-relaxed ${m.role === 'user' ? 'text-[#d4a017]' : 'text-[#e0e0e0]'}`}>
            <span className="text-[#555] mr-2">{m.role === 'user' ? 'you' : 'nexus'}</span>
            <Markdown>{m.content}</Markdown>
            {streaming && i === messages.length - 1 && m.role === 'assistant' && (
              <span className="animate-pulse">▋</span>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
      <div className="border-t border-[#1e1e1e] p-3 flex gap-2">
        <input
          className="flex-1 bg-[#111] border border-[#1e1e1e] text-xs px-3 py-2 rounded text-[#e0e0e0] outline-none focus:border-[#d4a017]"
          placeholder="/code · /think · or just ask..."
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && send()}
        />
        <button
          className="bg-[#d4a017] text-black text-xs px-3 py-2 rounded font-bold disabled:opacity-40"
          onClick={send}
          disabled={streaming}
        >
          send
        </button>
      </div>
    </div>
  )
}
