import axios from 'axios'

const api = axios.create({
  baseURL: '/api', // reverse-proxy should route /api to backend
  withCredentials: true, // send HttpOnly cookies
  timeout: 10000,
})

export default api
