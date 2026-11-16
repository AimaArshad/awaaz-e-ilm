import { Routes, Route } from 'react-router-dom'
import LibraryPage from './pages/LibraryPage'
import UploadPage from './pages/UploadPage'
import PlayerPage from './pages/PlayerPage'
import SettingsPage from './pages/SettingsPage'

export default function App() {
  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <Routes>
        <Route path="/" element={<LibraryPage />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/player/:documentId" element={<PlayerPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </div>
  )
}
