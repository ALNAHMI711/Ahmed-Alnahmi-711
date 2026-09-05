import React from 'react'

export default function MarketCard({ market }: { market: any }) {
  return (
    <div className="card mb-3">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm text-gray-300">{market.name}</div>
          <div className="text-2xl font-bold">{market.balance ?? '—'}</div>
          <div className="text-sm text-green-400">{market.pnl ?? '0.00'}</div>
        </div>
        <div className="text-right">
          <div className="text-sm">{market.status}</div>
          <button className="mt-2 px-3 py-1 bg-accent text-black rounded">تشغيل/إيقاف</button>
        </div>
      </div>
    </div>
  )
}
