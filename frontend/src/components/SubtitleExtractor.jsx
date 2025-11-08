import axios from 'axios'
import { useRef, useState } from 'react'
import Button from './Button'
import ProgressBar from './ProgressBar'

const API_BASE_URL = import.meta.env.VITE_API_URL

export default function SubtitleExtractor({ apiConnected }) {
  const [url, setUrl] = useState('')
  const [taskId, setTaskId] = useState(null)
  const [status, setStatus] = useState(null)
  const [progress, setProgress] = useState(0)
  const [subtitles, setSubtitles] = useState(null) // Array of subtitle objects
  const [selectedLang, setSelectedLang] = useState(0) // Index of selected language
  const [viewMode, setViewMode] = useState('single') // 'single' or 'dual'
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const [copySuccess, setCopySuccess] = useState(false)
  const pollIntervalRef = useRef(null)
  const progressAnimationRef = useRef(null)
  const lastRealProgressRef = useRef(0)
  const targetProgressRef = useRef(0)

  // Smooth progress animation
  const startProgressAnimation = () => {
    if (progressAnimationRef.current) {
      clearInterval(progressAnimationRef.current)
    }

    progressAnimationRef.current = setInterval(() => {
      setProgress((currentProgress) => {
        const target = targetProgressRef.current

        // If we're at or past the target, don't change
        if (currentProgress >= target) {
          return currentProgress
        }

        // Smooth increment - slower as we approach target
        const diff = target - currentProgress
        const increment = Math.max(0.5, diff * 0.1) // At least 0.5%, at most 10% of remaining

        return Math.min(currentProgress + increment, target)
      })
    }, 100) // Update every 100ms for smooth animation
  }

  const stopProgressAnimation = () => {
    if (progressAnimationRef.current) {
      clearInterval(progressAnimationRef.current)
      progressAnimationRef.current = null
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!url.trim()) {
      setError('請輸入有效的 YouTube 網址')
      return
    }

    setError(null)
    setLoading(true)
    setProgress(0)
    setStatus('pending')
    lastRealProgressRef.current = 0
    targetProgressRef.current = 0
    startProgressAnimation()

    try {
      const response = await axios.post(`${API_BASE_URL}/subtitles/extract`, {
        url: url.trim(),
      })

      const newTaskId = response.data.task_id
      setTaskId(newTaskId)
      pollForStatus(newTaskId)
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          err.message ||
          '提交任務失敗，請檢查 URL 是否正確'
      )
      setLoading(false)
    }
  }

  const pollForStatus = (id) => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current)
    }

    let pollCount = 0
    const maxPolls = 60 // Maximum 60 polls (3 seconds * 60 = 3 minutes max)

    pollIntervalRef.current = setInterval(async () => {
      pollCount++

      // Stop polling if exceeded maximum attempts
      if (pollCount > maxPolls) {
        clearInterval(pollIntervalRef.current)
        setError('提取超時，請重試。如果問題持續，可能是服務正在啟動中，請等待 1-2 分鐘後再試。')
        setLoading(false)
        return
      }

      try {
        const statusResponse = await axios.get(`${API_BASE_URL}/subtitles/status/${id}`)
        const taskStatus = statusResponse.data.status
        const realProgress = statusResponse.data.progress || 0

        setStatus(taskStatus)

        // Update target progress for smooth animation
        if (realProgress > lastRealProgressRef.current) {
          lastRealProgressRef.current = realProgress
          targetProgressRef.current = realProgress
        }

        // If still processing and progress hasn't changed, simulate slight progress
        if (taskStatus === 'processing' && realProgress === lastRealProgressRef.current && realProgress < 95) {
          // Slowly creep towards next milestone
          targetProgressRef.current = Math.min(realProgress + 3, 95)
        }

        if (taskStatus === 'completed') {
          targetProgressRef.current = 100
          setTimeout(() => {
            clearInterval(pollIntervalRef.current)
            stopProgressAnimation()
            fetchResult(id)
          }, 300) // Small delay to show 100%
        } else if (taskStatus === 'failed') {
          clearInterval(pollIntervalRef.current)
          stopProgressAnimation()
          const errorMessage = statusResponse.data.message || '字幕提取失敗'

          // Enhanced error message with helpful tips
          let enhancedError = errorMessage
          if (errorMessage.includes('bot') || errorMessage.includes('Sign in')) {
            enhancedError = `${errorMessage}\n\n可能原因：\n• 服務 IP 被 YouTube 暫時限制\n• 影片有地區限制或需要登入\n• 影片設有年齡限制\n\n建議：\n• 等待 5-10 分鐘後重試\n• 嘗試其他公開影片`
          } else if (errorMessage.includes('No subtitles')) {
            enhancedError = `${errorMessage}\n\n提示：\n• 該影片可能沒有字幕\n• 確認影片有啟用字幕功能\n• 嘗試有中文或英文字幕的影片`
          } else if (errorMessage.includes('403') || errorMessage.includes('Forbidden')) {
            enhancedError = `${errorMessage}\n\n可能原因：\n• YouTube 檢測到頻繁請求\n• 服務 IP 被暫時封鎖\n\n建議：等待 5-10 分鐘後重試`
          }

          setError(enhancedError)
          setLoading(false)
        }
      } catch (err) {
        console.error('Poll error:', err)
      }
    }, 2000) // Poll every 2 seconds for faster status updates
  }

  const fetchResult = async (id) => {
    try {
      const resultResponse = await axios.get(`${API_BASE_URL}/subtitles/result/${id}`)
      const data = resultResponse.data
      
      // Convert to array format if needed
      const subtitleArray = data.subtitles || []
      setSubtitles(subtitleArray)
      setSelectedLang(0) // Default to first language
      
      // Auto-enable dual view if we have 2 languages
      if (subtitleArray.length === 2) {
        setViewMode('dual')
      }
      
      setLoading(false)
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          err.message ||
          '獲取結果失敗'
      )
      setLoading(false)
    }
  }

  const handleDownload = (mode = 'single') => {
    if (!subtitles || subtitles.length === 0) return

    let content = ''
    let filename = `subtitles_${new Date().getTime()}`

    if (mode === 'single') {
      // Download selected language only
      content = subtitles[selectedLang].content
      filename += `_${subtitles[selectedLang].language.replace(/[^a-zA-Z0-9]/g, '_')}.txt`
    } else if (mode === 'dual-side' && subtitles.length >= 2) {
      // Download side-by-side (line by line interleaved)
      const lines1 = subtitles[0].content.split('\n')
      const lines2 = subtitles[1].content.split('\n')
      const maxLines = Math.max(lines1.length, lines2.length)
      
      for (let i = 0; i < maxLines; i++) {
        if (lines1[i]) content += lines1[i] + '\n'
        if (lines2[i]) content += lines2[i] + '\n'
        content += '\n' // Empty line between pairs
      }
      filename += '_dual.txt'
    } else if (mode === 'dual-parallel' && subtitles.length >= 2) {
      // Download parallel (two columns)
      const lines1 = subtitles[0].content.split('\n')
      const lines2 = subtitles[1].content.split('\n')
      const maxLines = Math.max(lines1.length, lines2.length)
      
      content = `${subtitles[0].language}\t${subtitles[1].language}\n`
      content += '='.repeat(80) + '\n\n'
      
      for (let i = 0; i < maxLines; i++) {
        const line1 = lines1[i] || ''
        const line2 = lines2[i] || ''
        content += `${line1}\t${line2}\n`
      }
      filename += '_parallel.txt'
    } else if (mode === 'all') {
      // Download all languages separately in one file
      subtitles.forEach((sub, index) => {
        content += `\n========== ${sub.language} ==========\n\n`
        content += sub.content + '\n\n'
      })
      filename += '_all.txt'
    }

    const element = document.createElement('a')
    const file = new Blob([content], { type: 'text/plain;charset=utf-8' })
    element.href = URL.createObjectURL(file)
    element.download = filename
    document.body.appendChild(element)
    element.click()
    document.body.removeChild(element)
  }

  const handleCopy = async () => {
    if (!subtitles || subtitles.length === 0) return
    
    try {
      let content = ''
      
      if (viewMode === 'single') {
        // Copy selected language only
        content = subtitles[selectedLang].content
      } else if (viewMode === 'dual' && subtitles.length >= 2) {
        // Copy both languages side by side
        const lines1 = subtitles[0].content.split('\n')
        const lines2 = subtitles[1].content.split('\n')
        const maxLines = Math.max(lines1.length, lines2.length)
        
        for (let i = 0; i < maxLines; i++) {
          if (lines1[i]) content += lines1[i] + '\n'
          if (lines2[i]) content += lines2[i] + '\n'
          content += '\n'
        }
      }
      
      await navigator.clipboard.writeText(content)
      setCopySuccess(true)
      setTimeout(() => setCopySuccess(false), 2000)
    } catch (err) {
      setError('複製失敗，請重試')
    }
  }

  const handleReset = () => {
    setUrl('')
    setTaskId(null)
    setStatus(null)
    setProgress(0)
    setSubtitles(null)
    setSelectedLang(0)
    setViewMode('single')
    setError(null)
    setLoading(false)
    setCopySuccess(false)
    lastRealProgressRef.current = 0
    targetProgressRef.current = 0
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current)
    }
    stopProgressAnimation()
  }

  return (
    <div className="space-y-10">
      {/* Input Section */}
      {!loading && !subtitles && (
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="url" className="block text-sm font-medium text-gray-700 mb-3">
              輸入 YouTube 網址
            </label>
            <input
              id="url"
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://www.youtube.com/watch?v=..."
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-800 placeholder-gray-400"
              disabled={!apiConnected}
              autoFocus
            />
            <p className="mt-2 text-xs text-gray-500">
              支援 YouTube 標準連結和短連結 (youtu.be)
            </p>
          </div>

          {error && (
            <div className="p-4 bg-red-50 border border-red-300 rounded-lg">
              <p className="text-sm text-red-700 font-medium whitespace-pre-line">{error}</p>
            </div>
          )}

          <Button
            type="submit"
            variant="primary"
            size="md"
            disabled={!apiConnected || !url.trim()}
          >
            提取字幕
          </Button>
        </form>
      )}

      {/* Progress Section */}
      {loading && (
        <div className="space-y-7">
          <div>
            <h2 className="text-lg font-semibold text-gray-800 mb-5">正在提取字幕...</h2>
            <ProgressBar progress={progress} status={status} />
          </div>

          <div className="text-sm text-gray-600">
            {status === 'pending' && '任務已提交，等候處理...'}
            {status === 'processing' && '正在提取字幕中，請稍候...'}
            {status === 'completed' && '提取完成！'}
          </div>
        </div>
      )}

      {/* Results Section */}
      {subtitles && subtitles.length > 0 && (
        <div className="space-y-7">
          {/* Success Message */}
          <div className="p-4 bg-green-50 border border-green-300 rounded-lg">
            <p className="text-sm text-green-700 font-medium">
              ✓ 成功提取 {subtitles.length} 個字幕：
              {subtitles.map((sub, i) => (
                <span key={i} className="ml-2">
                  {sub.language}
                  {sub.is_auto_generated && ' 🤖'}
                </span>
              ))}
            </p>
          </div>

          {/* Language Tabs (if multiple languages) */}
          {subtitles.length > 1 && (
            <div className="space-y-4">
              <div className="flex flex-wrap gap-2">
                {/* Language selection tabs */}
                {subtitles.map((sub, index) => (
                  <button
                    key={index}
                    onClick={() => {
                      setSelectedLang(index)
                      setViewMode('single')
                    }}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      selectedLang === index && viewMode === 'single'
                        ? 'bg-blue-500 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {sub.language}
                  </button>
                ))}
                
                {/* Dual view button (only if 2 languages) */}
                {subtitles.length === 2 && (
                  <button
                    onClick={() => setViewMode('dual')}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      viewMode === 'dual'
                        ? 'bg-blue-500 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    雙語對照
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Preview Card - Single Language View */}
          {viewMode === 'single' && (
            <div>
              <h2 className="text-lg font-semibold text-gray-800 mb-2">
                {subtitles[selectedLang].language}
              </h2>
              <p className="text-xs text-gray-500 mb-4">
                共 {subtitles[selectedLang].content.length.toLocaleString()} 個字符
              </p>

              <div className="bg-gray-50 border border-gray-300 rounded-lg p-5 font-mono text-sm text-gray-700 overflow-y-auto max-h-96 leading-relaxed">
                <pre className="whitespace-pre-wrap word-break">
                  {subtitles[selectedLang].content.substring(0, 1500)}
                  {subtitles[selectedLang].content.length > 1500 && '\n...'}
                </pre>
              </div>
            </div>
          )}

          {/* Preview Card - Dual Language View */}
          {viewMode === 'dual' && subtitles.length >= 2 && (
            <div>
              <h2 className="text-lg font-semibold text-gray-800 mb-2">雙語對照</h2>
              <p className="text-xs text-gray-500 mb-4">
                {subtitles[0].language} / {subtitles[1].language}
              </p>

              <div className="bg-gray-50 border border-gray-300 rounded-lg p-5 overflow-y-auto max-h-96">
                <div className="space-y-4">
                  {(() => {
                    const lines1 = subtitles[0].content.split('\n')
                    const lines2 = subtitles[1].content.split('\n')
                    const maxLines = Math.min(Math.max(lines1.length, lines2.length), 50) // Limit preview
                    
                    return Array.from({ length: maxLines }, (_, i) => (
                      <div key={i} className="space-y-1">
                        {lines1[i] && (
                          <p className="text-sm text-gray-800 font-mono">
                            {lines1[i]}
                          </p>
                        )}
                        {lines2[i] && (
                          <p className="text-sm text-blue-600 font-mono">
                            {lines2[i]}
                          </p>
                        )}
                      </div>
                    ))
                  })()}
                  <p className="text-xs text-gray-500 italic mt-4">
                    {Math.max(subtitles[0].content.split('\n').length, subtitles[1].content.split('\n').length) > 50 
                      ? '（預覽前 50 行，完整內容請下載）' 
                      : ''}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="space-y-3 pt-3">
            {/* Primary actions */}
            <div className="flex gap-3">
              <Button
                onClick={handleCopy}
                variant="outline"
                size="md"
              >
                {copySuccess ? '已複製 ✓' : '複製當前顯示'}
              </Button>
              <Button
                onClick={handleReset}
                variant="outline"
                size="md"
              >
                重新開始
              </Button>
            </div>

            {/* Download options */}
            <div className="space-y-2">
              <p className="text-sm font-medium text-gray-700">下載選項：</p>
              <div className="flex flex-wrap gap-2">
                {subtitles.map((sub, index) => (
                  <Button
                    key={index}
                    onClick={() => {
                      setSelectedLang(index)
                      handleDownload('single')
                    }}
                    variant="primary"
                    size="sm"
                  >
                    下載 {sub.language}
                  </Button>
                ))}
                
                {subtitles.length >= 2 && (
                  <>
                    <Button
                      onClick={() => handleDownload('dual-side')}
                      variant="primary"
                      size="sm"
                    >
                      下載雙語對照（逐行）
                    </Button>
                    <Button
                      onClick={() => handleDownload('dual-parallel')}
                      variant="primary"
                      size="sm"
                    >
                      下載雙語對照（並排）
                    </Button>
                    <Button
                      onClick={() => handleDownload('all')}
                      variant="primary"
                      size="sm"
                    >
                      下載全部
                    </Button>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
