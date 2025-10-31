/**
 * StatusBadge Component - 狀態指示器
 */

export default function StatusBadge({ status, message }) {
  const getStyles = () => {
    switch (status) {
      case 'connected':
        return {
          bg: 'bg-green-50',
          border: 'border-green-200',
          text: 'text-green-800',
          dot: 'bg-green-500',
        }
      case 'checking':
        return {
          bg: 'bg-blue-50',
          border: 'border-blue-200',
          text: 'text-blue-800',
          dot: 'bg-blue-500',
        }
      case 'disconnected':
        return {
          bg: 'bg-red-50',
          border: 'border-red-200',
          text: 'text-red-800',
          dot: 'bg-red-500',
        }
      case 'success':
        return {
          bg: 'bg-green-50',
          border: 'border-green-200',
          text: 'text-green-800',
          dot: 'bg-green-500',
        }
      case 'error':
        return {
          bg: 'bg-red-50',
          border: 'border-red-200',
          text: 'text-red-800',
          dot: 'bg-red-500',
        }
      case 'warning':
        return {
          bg: 'bg-yellow-50',
          border: 'border-yellow-200',
          text: 'text-yellow-800',
          dot: 'bg-yellow-500',
        }
      default:
        return {
          bg: 'bg-gray-50',
          border: 'border-gray-200',
          text: 'text-gray-800',
          dot: 'bg-gray-500',
        }
    }
  }

  const styles = getStyles()

  return (
    <div className={`${styles.bg} border ${styles.border} rounded-lg p-4`}>
      <div className="flex items-center gap-3">
        <div className={`w-2 h-2 rounded-full ${styles.dot}`} />
        <p className={`text-sm font-medium ${styles.text}`}>{message}</p>
      </div>
    </div>
  )
}
