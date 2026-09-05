import React from 'react'
import { Link } from 'react-router-dom'

export default function Nav() {
  return (
    <nav className="flex gap-3 mb-4">
      <Link to="/" className="px-3 py-1 rounded bg-gray-800">الصفحة الرئيسية</Link>
      <Link to="/api-accounts" className="px-3 py-1 rounded bg-gray-800">حسابات API</Link>
      <Link to="/strategies" className="px-3 py-1 rounded bg-gray-800">إدارة الاستراتيجيات</Link>
      <Link to="/backtests" className="px-3 py-1 rounded bg-gray-800">Backtests</Link>
      <Link to="/settings" className="px-3 py-1 rounded bg-gray-800">الإعدادات</Link>
    </nav>
  )
}
