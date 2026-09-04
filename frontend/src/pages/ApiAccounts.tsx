import React from 'react'
import Layout from '../components/Layout'
import ApiAccountModal from '../components/ApiAccountModal'
import ApiAccountList from '../components/ApiAccountList'
import Nav from '../components/Nav'

export default function ApiAccountsPage() {
  return (
    <Layout>
      <Nav />
      <div className="grid gap-4 grid-cols-1 lg:grid-cols-2">
        <div>
          <ApiAccountModal />
        </div>
        <div>
          <ApiAccountList />
        </div>
      </div>
    </Layout>
  )
}
