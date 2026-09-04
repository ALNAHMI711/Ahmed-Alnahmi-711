import React, { useState } from 'react'
import { useMutation, useQueryClient } from 'react-query'
import { createApiAccount } from '../services/apiAccounts'

export default function ApiAccountModal() {
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [exchange, setExchange] = useState('binance')
  const [apiKey, setApiKey] = useState('')
  const [apiSecret, setApiSecret] = useState('')
  const qc = useQueryClient()

  const createMut = useMutation((payload: any) => createApiAccount(payload), {
    onSuccess: () => {
      qc.invalidateQueries(['apiAccounts'])
      setOpen(false)
      setName('')
      setApiKey('')
      setApiSecret('')
    }
  })

  return (
    <div>
      <button className="px-3 py-1 bg-accent text-black rounded" onClick={() => setOpen(true)}>إضافة حساب API</button>
      {open && (
        <div className="card mt-3">
          <h3 className="mb-2">إضافة حساب API</h3>
          <input dir="rtl" placeholder="الاسم" className="w-full mb-2 p-2 rounded bg-gray-900" value={name} onChange={e => setName(e.target.value)} />
          <select value={exchange} onChange={e => setExchange(e.target.value)} className="w-full mb-2 p-2 rounded bg-gray-900">
            <option value="binance">Binance</option>
            <option value="ftx">FTX</option>
          </select>
          <input dir="rtl" placeholder="API Key" className="w-full mb-2 p-2 rounded bg-gray-900" value={apiKey} onChange={e => setApiKey(e.target.value)} />
          <input dir="rtl" placeholder="API Secret" className="w-full mb-2 p-2 rounded bg-gray-900" value={apiSecret} onChange={e => setApiSecret(e.target.value)} />
          <div className="flex gap-2">
            <button className="px-3 py-1 bg-accent text-black rounded" onClick={() => createMut.mutate({ user_id: '00000000-0000-0000-0000-000000000000', name, exchange, api_key: apiKey, api_secret: apiSecret })}>إنشاء</button>
            <button className="px-3 py-1 bg-gray-700 rounded" onClick={() => setOpen(false)}>إلغاء</button>
          </div>
          {createMut.isError && <div className="text-red-400 mt-2">فشل الإنشاء</div>}
        </div>
      )}
    </div>
  )
}
