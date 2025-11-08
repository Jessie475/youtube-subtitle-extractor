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
          import.meta.env.VITE_API_URL ,
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
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
      {/* Decorative background elements */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-blue-400 rounded-full mix-blend-multiply filter blur-xl opacity-10 animate-blob"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-indigo-400 rounded-full mix-blend-multiply filter blur-xl opacity-10 animate-blob animation-delay-2000"></div>
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-80 h-80 bg-purple-400 rounded-full mix-blend-multiply filter blur-xl opacity-10 animate-blob animation-delay-4000"></div>
      </div>

      {/* Content */}
      <div className="relative z-10">
        {/* Header */}
        <header className="border-b border-white/50 bg-white/30 backdrop-blur-md">
          <div className="max-w-6xl mx-auto px-8 py-8">
            <div className="flex items-center justify-between">
              {/* Logo and Title */}
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-xl flex items-center justify-center shadow-lg">
                  <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" />
                  </svg>
                </div>
                <div>
                  <h1 className="text-2xl font-bold bg-gradient-to-r from-gray-900 to-gray-700 bg-clip-text text-transparent">
                    YouTube 字幕提取工具
                  </h1>
                  <p className="text-sm text-gray-500">快速、免費、無需登入</p>
                </div>
              </div>

              {/* Status indicator */}
              <div className="flex items-center gap-3 px-4 py-2 rounded-full bg-white/50 backdrop-blur-sm border border-white/60">
                <div className={`w-2.5 h-2.5 rounded-full ${apiConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></div>
                <span className="text-sm font-medium text-gray-700">
                  {apiConnected ? '服務正常' : '服務離線'}
                </span>
              </div>
            </div>
          </div>
        </header>

        {/* Hero Section */}
        <div className="max-w-6xl mx-auto px-8 pt-20 pb-12">
          <div className="text-center mb-16">
            <h2 className="text-5xl md:text-6xl font-extrabold text-gray-900 mb-6 leading-tight">
              輕鬆提取 YouTube 字幕
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              支援多語言字幕、自動生成字幕，一鍵複製或下載為 TXT 文件
            </p>

            {/* Feature badges */}
            <div className="flex flex-wrap justify-center gap-4 mt-8">
              <span className="px-6 py-3 bg-white/60 backdrop-blur-sm rounded-full text-base font-medium text-gray-700 border border-white/80 shadow-sm">
                ✨ 完全免費
              </span>
              <span className="px-6 py-3 bg-white/60 backdrop-blur-sm rounded-full text-base font-medium text-gray-700 border border-white/80 shadow-sm">
                🌐 支援多語言
              </span>
              <span className="px-6 py-3 bg-white/60 backdrop-blur-sm rounded-full text-base font-medium text-gray-700 border border-white/80 shadow-sm">
                🚀 快速提取
              </span>
            </div>
          </div>

          {/* Main Card */}
          <div className="bg-white/70 backdrop-blur-lg rounded-2xl shadow-xl border border-white/80 p-12 md:p-14">
            <SubtitleExtractor apiConnected={apiConnected} />
          </div>

          {/* How it works */}
          <div className="mt-24 mb-16">
            <h3 className="text-3xl font-bold text-gray-900 text-center mb-12">
              如何使用
            </h3>
            <div className="grid md:grid-cols-3 gap-8">
              {[
                {
                  step: '1',
                  icon: (
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                    </svg>
                  ),
                  title: '複製影片連結',
                  desc: '從 YouTube 複製想要提取字幕的影片網址'
                },
                {
                  step: '2',
                  icon: (
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122" />
                    </svg>
                  ),
                  title: '貼上並提取',
                  desc: '貼上連結，點擊提取按鈕，等待處理完成'
                },
                {
                  step: '3',
                  icon: (
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2" />
                    </svg>
                  ),
                  title: '複製或下載',
                  desc: '字幕提取完成後，可一鍵複製或下載為文件'
                }
              ].map((item, index) => (
                <div key={index} className="bg-white/50 backdrop-blur-sm rounded-xl p-8 border border-white/60 hover:shadow-lg transition-shadow">
                  <div className="flex items-center gap-4 mb-4">
                    <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center text-white text-lg font-bold shadow-md">
                      {item.step}
                    </div>
                    <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center text-blue-600">
                      {item.icon}
                    </div>
                  </div>
                  <h4 className="text-xl font-semibold text-gray-900 mb-3">{item.title}</h4>
                  <p className="text-base text-gray-600">{item.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <footer className="border-t border-white/50 bg-white/30 backdrop-blur-md mt-32">
          <div className="max-w-6xl mx-auto px-8 py-10">
            <div className="flex flex-col md:flex-row items-center justify-between gap-6">
              <div className="text-base text-gray-600">
                © 2025 YouTube 字幕提取工具 · 由{' '}
                <a
                  href="https://kokonut.us.kg"
                  className="text-blue-600 hover:text-blue-700 font-medium transition-colors"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  kokonut.us.kg
                </a>{' '}
                提供
              </div>
              <div className="flex items-center gap-5 text-base text-gray-500">
                <span>完全免費</span>
                <span>·</span>
                <span>無需註冊</span>
                <span>·</span>
                <span>開源專案</span>
              </div>
            </div>
          </div>
        </footer>
      </div>
    </div>
  )
}

export default App
