import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { uploadStrategy, fetchStrategies } from '../services/strategies'

export default function StrategyUpload() {
  const [file, setFile] = useState<File | null>(null)
  const qc = useQueryClient()
  const uploadMut = useMutation((fd: FormData) => uploadStrategy(fd), {
    onSuccess: () => qc.invalidateQueries(['strategies'])
  })

  function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!file) return alert('اختر ملفاً')
    const fd = new FormData()
    fd.append('file', file)
    uploadMut.mutate(fd)
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
      {uploadMut.isLoading && <div className="mt-2">جارٍ الرفع...</div>}
      {uploadMut.isError && <div className="mt-2 text-red-400">فشل الرفع</div>}
    </div>
  )
}
