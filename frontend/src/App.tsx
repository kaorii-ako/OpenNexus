import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Chat from './views/Chat'
import Digest from './views/Digest'
import NotionView from './views/Notion'
import Status from './views/Status'

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen bg-[#0a0a0a] text-[#e0e0e0] font-mono">
        <Sidebar />
        <main className="flex-1 overflow-auto">
          <Routes>
            <Route path="/" element={<Navigate to="/digest" />} />
            <Route path="/digest" element={<Digest />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/notion" element={<NotionView />} />
            <Route path="/status" element={<Status />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
