import axios from 'axios'
import { useEffect, useState } from 'react'
import './App.css'
import SubtitleExtractor from './components/SubtitleExtractor'

function App() {
  const [apiConnected, setApiConnected] = useState(true)

  useEffect(() => {
    // Silent health check - only used for internal tracking
    const checkHealth = async () => {
      try {
        await axios.get(
          import.meta.env.VITE_API_URL || 'http://localhost:8000',
          { timeout: 5000 }
        )
        setApiConnected(true)
      } catch (error) {
        setApiConnected(false)
        console.error('API Connection Error:', error.message)
      }
    }

    checkHealth()
  }, [])

  return (
    <div className="min-h-screen bg-blue-50 flex flex-col">
      {/* Header */}
      <header className="border-b border-blue-200 bg-gradient-to-r from-blue-50 to-blue-100">
        <div className="max-w-5xl mx-auto px-12 py-16">
          <div className="flex items-center gap-3 mb-3">
            <svg className="w-10 h-10 text-red-600" fill="currentColor" viewBox="0 0 24 24">
              <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
            </svg>
            <h1 className="text-4xl font-bold text-gray-800">
              YouTube 字幕提取
            </h1>
          </div>
          <p className="text-lg text-gray-600 ml-13">
            輕鬆提取 YouTube 影片字幕，支持多語言和自動字幕
          </p>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-5xl w-full mx-auto px-12 py-16">
        <SubtitleExtractor apiConnected={apiConnected} />
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-700 bg-gray-900 mt-24">
        <div className="max-w-5xl mx-auto px-12 py-10 text-center">
          <p className="text-gray-400 text-sm">
            © 2025 YouTube 字幕提取 | 由{' '}
            <a
              href="https://kokonut.us.kg"
              className="text-gray-200 hover:text-blue-400 font-medium transition-colors"
              target="_blank"
              rel="noopener noreferrer"
            >
              kokonut.us.kg
            </a>{' '}
            提供
          </p>
        </div>
      </footer>
    </div>
  )
}

export default App
