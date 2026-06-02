import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Dashboard from './views/Dashboard'
import Chat from './views/Chat'
import Digest from './views/Digest'
import NotionView from './views/Notion'
import Settings from './views/Settings'

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen bg-[#0a0a0a] text-[#e0e0e0] font-mono">
        <Sidebar />
        <main className="flex-1 overflow-auto">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/digest" element={<Digest />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/notion" element={<NotionView />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
