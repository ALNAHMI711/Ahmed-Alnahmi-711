import React from 'react'
import Layout from '../components/Layout'
import MarketCard from '../components/MarketCard'
import NotificationToast from '../components/NotificationToast'
import useWebSocket from '../hooks/useWebSocket'

const demoMarkets = [
  { name: 'تداول فوري', balance: '1,250.00 USDT', pnl: '+12.3%', status: '🟢 يعمل' },
  { name: 'USDⓈ-M Futures', balance: '0.00', pnl: '-0.5%', status: '🔵 اختبار' }
]

export default function Dashboard() {
  useWebSocket('/ws/events')

  return (
    <Layout>
      <NotificationToast />
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 md:grid-cols-3">
        {demoMarkets.map((m) => (
          <MarketCard key={m.name} market={m} />
        ))}
      </div>
    </Layout>
  )
}
