import api from '../services/api'

export async function fetchApiAccounts() {
  const r = await api.get('/v1/api-accounts/')
  return r.data
}

export async function createApiAccount(payload: any) {
  const r = await api.post('/v1/api-accounts/', payload)
  return r.data
}

export async function testApiAccount(id: string) {
  const r = await api.post(`/v1/api-accounts/${id}/test`)
  return r.data
}
