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
  const [subtitles, setSubtitles] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const [copySuccess, setCopySuccess] = useState(false)
  const pollIntervalRef = useRef(null)

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

        setStatus(taskStatus)
        setProgress(statusResponse.data.progress || 0)

        if (taskStatus === 'completed') {
          clearInterval(pollIntervalRef.current)
          fetchResult(id)
        } else if (taskStatus === 'failed') {
          clearInterval(pollIntervalRef.current)
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
    }, 3000) // Poll every 3 seconds instead of 1 second (reduces requests by 67%)
  }

  const fetchResult = async (id) => {
    try {
      const resultResponse = await axios.get(`${API_BASE_URL}/subtitles/result/${id}`)
      setSubtitles(resultResponse.data)
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

  const handleDownload = () => {
    if (!subtitles?.content) return

    const element = document.createElement('a')
    const file = new Blob([subtitles.content], { type: 'text/plain;charset=utf-8' })
    element.href = URL.createObjectURL(file)
    element.download = `subtitles_${new Date().getTime()}.txt`
    document.body.appendChild(element)
    element.click()
    document.body.removeChild(element)
  }

  const handleCopy = async () => {
    if (!subtitles?.content) return
    try {
      await navigator.clipboard.writeText(subtitles.content)
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
    setError(null)
    setLoading(false)
    setCopySuccess(false)
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current)
    }
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
      {subtitles && (
        <div className="space-y-7">
          {/* Success Message */}
          <div className="p-4 bg-green-50 border border-green-300 rounded-lg">
            <p className="text-sm text-green-700 font-medium">
              ✓ 成功提取字幕 ({subtitles.language})
            </p>
          </div>

          {/* Preview Card */}
          <div>
            <h2 className="text-lg font-semibold text-gray-800 mb-2">字幕內容</h2>
            <p className="text-xs text-gray-500 mb-4">共 {subtitles.content.length.toLocaleString()} 個字符</p>

            <div className="bg-gray-50 border border-gray-300 rounded-lg p-5 font-mono text-sm text-gray-700 overflow-y-auto max-h-96 leading-relaxed">
              <pre className="whitespace-pre-wrap word-break">{subtitles.content.substring(0, 1500)}{subtitles.content.length > 1500 && '\n...'}</pre>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 pt-3">
            <Button
              onClick={handleDownload}
              variant="primary"
              size="md"
            >
              下載
            </Button>
            <Button
              onClick={handleCopy}
              variant="outline"
              size="md"
            >
              {copySuccess ? '已複製' : '複製'}
            </Button>
            <Button
              onClick={handleReset}
              variant="outline"
              size="md"
            >
              重新開始
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
