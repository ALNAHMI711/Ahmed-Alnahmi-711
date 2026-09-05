import React from 'react'
import { useQuery } from 'react-query'
import { fetchStrategies } from '../services/strategies'

export default function StrategyList() {
  const { data, isLoading } = useQuery(['strategies'], fetchStrategies)
  if (isLoading) return <div>جارٍ التحميل...</div>
  if (!data || data.length === 0) return <div className="card">لا توجد استراتيجيات</div>
  return (
    <div className="space-y-3">
      {data.map((s: any) => (
        <div key={s.id} className="card flex items-center justify-between">
          <div>
            <div className="text-sm">{s.name} — {s.version}</div>
            <div className="text-xs text-gray-400">{s.status}</div>
          </div>
          <div>
            <button className="px-3 py-1 bg-gray-700 rounded mr-2">تفاصيل</button>
            <button className="px-3 py-1 bg-gray-700 rounded">حذف</button>
          </div>
        </div>
      ))}
    </div>
  )
}
