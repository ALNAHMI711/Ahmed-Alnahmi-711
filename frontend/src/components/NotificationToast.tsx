import React, { useEffect, useState } from 'react'

type Toast = { id: number, type: string, message: string }

export default function NotificationToast() {
  const [toasts, setToasts] = useState<Toast[]>([])

  useEffect(() => {
    function handler(e: any) {
      const detail = e.detail || {}
      const id = Date.now() + Math.floor(Math.random()*1000)
      setToasts(t => [...t, { id, type: detail.type || 'info', message: detail.message || '' }])
      setTimeout(() => {
        setToasts(t => t.filter(x => x.id !== id))
      }, 6000)
    }
    window.addEventListener('notify', handler as EventListener)
    return () => window.removeEventListener('notify', handler as EventListener)
  }, [])

  if (toasts.length === 0) return null

  return (
    <div className="fixed bottom-4 left-4 z-50 space-y-2">
      {toasts.map(t => (
        <div key={t.id} className={`p-3 rounded shadow ${t.type === 'error' ? 'bg-red-600' : t.type === 'success' ? 'bg-green-600' : 'bg-gray-800'}`}>
          <div className="text-sm">{t.message}</div>
        </div>
      ))}
    </div>
  )
}
