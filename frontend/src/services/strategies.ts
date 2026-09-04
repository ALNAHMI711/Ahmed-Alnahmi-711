import api from './api'

export async function uploadStrategy(formData: FormData) {
  const r = await api.post('/v1/strategies/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return r.data
}

export async function fetchStrategies() {
  const r = await api.get('/v1/strategies/')
  return r.data
}
