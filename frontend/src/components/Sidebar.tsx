import { NavLink } from 'react-router-dom'

const links = [
  { to: '/digest', label: '📋 Digest' },
  { to: '/chat', label: '💬 Chat' },
  { to: '/notion', label: '📝 Notion' },
  { to: '/status', label: '⚡ Status' },
]

export default function Sidebar() {
  return (
    <nav className="w-44 border-r border-[#1e1e1e] flex flex-col p-4 gap-2 shrink-0">
      <div className="text-[#d4a017] font-bold text-sm mb-4">NEXUS</div>
      {links.map(l => (
        <NavLink
          key={l.to}
          to={l.to}
          className={({ isActive }) =>
            `text-xs px-2 py-1.5 rounded transition-colors ${
              isActive ? 'bg-[#1e1e1e] text-[#d4a017]' : 'text-[#555] hover:text-[#e0e0e0]'
            }`
          }
        >
          {l.label}
        </NavLink>
      ))}
    </nav>
  )
}
