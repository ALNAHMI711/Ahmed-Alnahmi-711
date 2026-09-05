import React, { useEffect, useState } from 'react'
import api from '../services/api'
import { testApiAccount } from '../services/apiAccounts'

export default function ApiAccountTestModal({ account, onClose }: { account: any, onClose: ()=>void }) {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function runTest() {
      setLoading(true)
      setError(null)
      try {
        const res = await testApiAccount(account.id)
        setResult(res)
        // dispatch notification
        window.dispatchEvent(new CustomEvent('notify', { detail: { type: 'success', message: `Test completed for ${account.name}` } }))
      } catch (err: any) {
        setError(err?.message || 'فشل اختبار الحساب')
        window.dispatchEvent(new CustomEvent('notify', { detail: { type: 'error', message: `Test failed for ${account.name}` } }))
      } finally {
        setLoading(false)
      }
    }
    runTest()
  }, [account])

  return (
    <div className="fixed inset-0 flex items-center justify-center z-50">
      <div className="absolute inset-0 bg-black/50" onClick={onClose}></div>
      <div className="card w-full max-w-lg z-60">
        <h3 className="text-lg mb-2">نتيجة اختبار الحساب — {account.name}</h3>
        {loading && <div>جارٍ الاختبار...</div>}
        {error && <div className="text-red-400">{error}</div>}
        {result && (
          <div className="space-y-2">
            <div><strong>الحالة:</strong> {result.ok ? 'نجاح' : 'فشل'}</div>
            <div><strong>IP restricted:</strong> {String(result.ip_restricted)}</div>
            <div><strong>Permissions:</strong> {Array.isArray(result.permissions) ? result.permissions.join(', ') : JSON.stringify(result.permissions)}</div>
            <div><strong>Raw:</strong></div>
            <pre className="bg-black/40 p-2 rounded text-xs overflow-auto max-h-48">{JSON.stringify(result, null, 2)}</pre>
          </div>
        )}
        <div className="mt-4 flex justify-end gap-2">
          <button className="px-3 py-1 bg-gray-700 rounded" onClick={onClose}>إغلاق</button>
        </div>
      </div>
    </div>
  )
}
