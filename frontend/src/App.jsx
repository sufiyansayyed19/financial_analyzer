import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import Dashboard from './pages/Dashboard'
import AskSearch from './pages/AskSearch'
import Upload from './pages/Upload'

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-surface-900">
        {/* Subtle gradient background */}
        <div className="fixed inset-0 -z-10">
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-brand-600/10 rounded-full blur-3xl" />
          <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-purple-600/10 rounded-full blur-3xl" />
        </div>

        <Navbar />

        <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/ask" element={<AskSearch />} />
            <Route path="/upload" element={<Upload />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App
