import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { fetchApiAccounts } from '../services/apiAccounts'
import ApiAccountTestModal from './ApiAccountTestModal'

export default function ApiAccountList() {
  const qc = useQueryClient()
  const { data, isLoading } = useQuery(['apiAccounts'], fetchApiAccounts)
  const [selected, setSelected] = useState<any | null>(null)

  if (isLoading) return <div>جارٍ التحميل...</div>

  return (
    <div>
      {!data || data.length === 0 ? (
        <div className="card">لا توجد حسابات حتى الآن</div>
      ) : (
        <div className="space-y-3">
          {data.map((acc: any) => (
            <div key={acc.id} className="card flex items-center justify-between">
              <div>
                <div className="text-sm">{acc.name} — {acc.exchange}</div>
                <div className="text-xs text-gray-400">مُنشأ: {new Date(acc.created_at).toLocaleString()}</div>
              </div>
              <div className="flex gap-2">
                <button className="px-3 py-1 bg-gray-700 rounded" onClick={() => setSelected(acc)}>
                  اختبار
                </button>
                <button className="px-3 py-1 bg-red-600 rounded">حذف</button>
              </div>
            </div>
          ))}
        </div>
      )}

      {selected && (
        <ApiAccountTestModal account={selected} onClose={() => setSelected(null)} />
      )}

    </div>
  )
}
