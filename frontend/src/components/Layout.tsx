import React, { ReactNode } from 'react'

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="p-4 sm:p-6 md:p-8">
      <header className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-semibold">منصة التداول السحابية</h1>
        <div className="text-sm text-gray-400">الحالة: 🟢 يعمل</div>
      </header>
      <main>{children}</main>
    </div>
  )
}
