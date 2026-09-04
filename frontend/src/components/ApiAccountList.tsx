import React from 'react'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { fetchApiAccounts, testApiAccount } from '../services/apiAccounts'

export default function ApiAccountList() {
  const qc = useQueryClient()
  const { data, isLoading } = useQuery(['apiAccounts'], fetchApiAccounts)
  const testMut = useMutation((id: string) => testApiAccount(id), {
    onSuccess: () => qc.invalidateQueries(['apiAccounts'])
  })

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
                <button className="px-3 py-1 bg-gray-700 rounded" onClick={() => testMut.mutate(acc.id)}>
                  اختبار
                </button>
                <button className="px-3 py-1 bg-red-600 rounded">حذف</button>
              </div>
            </div>
          ))}
        </div>
      )}
      {testMut.isLoading && <div className="mt-2">جارٍ اختبار الحساب...</div>}
      {testMut.isError && <div className="mt-2 text-red-400">فشل اختبار الحساب</div>}
    </div>
  )
}
