import React, { useState } from 'react'
import { useQueryClient } from 'react-query'
import { uploadStrategy } from '../services/strategies'

export default function StrategyUpload() {
  const [file, setFile] = useState<File | null>(null)
  const [progress, setProgress] = useState(0)
  const qc = useQueryClient()

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!file) return alert('اختر ملفاً')
    const fd = new FormData()
    fd.append('file', file)
    try {
      setProgress(0)
      await uploadStrategy(fd, (ev: ProgressEvent) => {
        if (ev.lengthComputable) {
          const pct = Math.round((ev.loaded / ev.total) * 100)
          setProgress(pct)
        }
      })
      qc.invalidateQueries(['strategies'])
      setFile(null)
      window.dispatchEvent(new CustomEvent('notify', { detail: { type: 'success', message: 'تم رفع الاستراتيجية بنجاح' } }))
    } catch (err) {
      window.dispatchEvent(new CustomEvent('notify', { detail: { type: 'error', message: 'فشل رفع الاستراتيجية' } }))
    } finally {
      setTimeout(() => setProgress(0), 800)
    }
  }

  return (
    <div className="card">
      <h3 className="mb-2">رفع استراتيجية</h3>
      <form onSubmit={submit}>
        <input type="file" accept=".py,.zip" onChange={e => setFile(e.target.files ? e.target.files[0] : null)} />
        <div className="mt-2">
          <button className="px-3 py-1 bg-accent text-black rounded" type="submit">رفع</button>
        </div>
      </form>
      {progress > 0 && (
        <div className="mt-3">
          <div className="w-full bg-gray-700 h-3 rounded overflow-hidden">
            <div className="h-3 bg-accent" style={{ width: `${progress}%` }}></div>
          </div>
          <div className="text-sm text-gray-400 mt-1">{progress}%</div>
        </div>
      )}
    </div>
  )
}
