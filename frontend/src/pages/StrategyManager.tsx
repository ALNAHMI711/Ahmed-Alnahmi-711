import React from 'react'
import Layout from '../components/Layout'
import Nav from '../components/Nav'
import StrategyUpload from '../components/StrategyUpload'
import StrategyList from '../components/StrategyList'

export default function StrategyManager() {
  return (
    <Layout>
      <Nav />
      <div className="grid gap-4 grid-cols-1 lg:grid-cols-2">
        <div>
          <StrategyUpload />
        </div>
        <div>
          <StrategyList />
        </div>
      </div>
    </Layout>
  )
}
