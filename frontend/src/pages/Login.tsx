import React, { useState } from 'react'
import api from '../services/api'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    try {
      await api.post('/v1/auth/login', new URLSearchParams({ username, password }))
      window.location.href = '/'
    } catch (err) {
      alert('فشل تسجيل الدخول')
    } finally {
      setLoading(false)
    }
  }
  return (
    <div className="min-h-screen flex items-center justify-center">
      <form onSubmit={submit} className="w-full max-w-sm card">
        <h2 className="text-xl mb-4">تسجيل الدخول</h2>
        <input dir="rtl" className="w-full mb-2 p-2 rounded bg-gray-900" placeholder="اسم المستخدم" value={username} onChange={(e)=>setUsername(e.target.value)} />
        <input dir="rtl" type="password" className="w-full mb-4 p-2 rounded bg-gray-900" placeholder="كلمة المرور" value={password} onChange={(e)=>setPassword(e.target.value)} />
        <button type="submit" className="w-full py-2 bg-accent rounded">{loading ? 'جارٍ...' : 'دخول'}</button>
      </form>
    </div>
  )
}
