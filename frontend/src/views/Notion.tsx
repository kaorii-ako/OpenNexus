import { useEffect, useState } from 'react'
import { getNotionTree, getNotionPage, searchNotion } from '../lib/api'
import Markdown from '../components/Markdown'

export default function NotionView() {
  const [pages, setPages] = useState<{id: string; title: string}[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [content, setContent] = useState('')
  const [search, setSearch] = useState('')

  useEffect(() => { getNotionTree().then(d => setPages(d.pages || [])) }, [])

  async function loadPage(id: string) {
    setSelected(id)
    const d = await getNotionPage(id)
    setContent(d.content_md || '')
  }

  async function doSearch() {
    if (!search.trim()) return
    const d = await searchNotion(search)
    setPages(d.results || [])
  }

  return (
    <div className="flex h-full">
      <div className="w-56 border-r border-[#1e1e1e] p-3 overflow-auto">
        <input
          className="w-full bg-[#111] border border-[#1e1e1e] text-xs px-2 py-1 rounded mb-3 text-[#e0e0e0]"
          placeholder="search..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && doSearch()}
        />
        {pages.map(p => (
          <button
            key={p.id}
            className={`block w-full text-left text-xs px-2 py-1 rounded mb-0.5 ${selected === p.id ? 'text-[#d4a017]' : 'text-[#555] hover:text-[#e0e0e0]'}`}
            onClick={() => loadPage(p.id)}
          >
            {p.title}
          </button>
        ))}
      </div>
      <div className="flex-1 p-6 overflow-auto">
        {content
          ? <div className="prose prose-invert prose-sm max-w-none text-xs"><Markdown>{content}</Markdown></div>
          : <p className="text-[#555] text-xs">Select a page</p>}
      </div>
    </div>
  )
}
