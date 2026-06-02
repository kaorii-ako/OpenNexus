import { NavLink } from 'react-router-dom'

const links = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/chat', label: 'Chat' },
  { to: '/digest', label: 'Briefing' },
  { to: '/notion', label: 'Notion' },
  { to: '/settings', label: 'Settings' },
]

export default function Sidebar() {
  return (
    <nav className="w-40 border-r border-[#1a1a1a] flex flex-col p-4 gap-1 shrink-0">
      <div className="text-[#d4a017] font-bold text-xs tracking-widest mb-5 uppercase">NEXUS</div>
      {links.map(l => (
        <NavLink
          key={l.to}
          to={l.to}
          className={({ isActive }) =>
            `text-xs px-2 py-1.5 rounded transition-colors ${
              isActive ? 'bg-[#1a1a1a] text-[#d4a017]' : 'text-[#444] hover:text-[#e0e0e0]'
            }`
          }
        >
          {l.label}
        </NavLink>
      ))}
    </nav>
  )
}
