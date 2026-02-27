import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || 'http://localhost:8080',
  timeout: 60000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

// --- Auth ---
export const login = (username: string, password: string) =>
  api.post('/api/auth/login', new URLSearchParams({ username, password }))

// --- Config ---
export const getProxyConfig = () => api.get('/api/config/proxy')
export const setProxyConfig = (data: any) => api.post('/api/config/proxy', data)

// --- Collect ---
export const startCollect = (data: any) => api.post('/api/collect/start', data)
export const stopCollect = (data: any) => api.post('/api/collect/stop', data)
export const getCollectStatus = () => api.get('/api/collect/status')
export const listCollectTasks = () => api.get('/api/collect/tasks')

// --- Files ---
export const listTaskFiles = () => api.get('/api/files/tasks')
export const getPerformanceData = (taskId: string, page = 1, size = 20) =>
  api.get(`/api/files/${taskId}/performance`, { params: { page, size } })
export const getQAData = (taskId: string, page = 1, size = 20) =>
  api.get(`/api/files/${taskId}/qa`, { params: { page, size } })
export const getSummary = (taskId: string) => api.get(`/api/files/${taskId}/summary`)

// --- Metrics ---
export const getDistributions = (taskId: string) =>
  api.get(`/api/metrics/${taskId}/distributions`)
export const getMetricsSummary = (taskId: string) =>
  api.get(`/api/metrics/${taskId}/summary`)

// --- Benchmark ---
export const startBenchmark = (data: any) => api.post('/api/benchmark/start', data)
export const getBenchmarkProgress = (taskId: string) =>
  api.get(`/api/benchmark/${taskId}/progress`)
export const listBenchmarkTasks = () => api.get('/api/benchmark/tasks')

// --- Compare ---
export const compareTasks = (baselineId: string, optimizedId: string) =>
  api.get('/api/compare', { params: { baseline_id: baselineId, optimized_id: optimizedId } })

// --- Report ---
export const generateReport = (data: any) => api.post('/api/report/generate', data)
export const listReports = () => api.get('/api/report/list')
export const downloadReportUrl = (reportId: string) =>
  `${api.defaults.baseURL}/api/report/download/${reportId}`

// --- Analysis ---
export const listEngines = () => api.get('/api/analysis/engines')
export const getSuggestions = (taskId: string) =>
  api.get(`/api/analysis/${taskId}/suggestions`)

// --- Mock (dev only) ---
if (import.meta.env.VITE_USE_MOCK === 'true') {
  import('./mock').then(({ setupMock }) => setupMock(api))
}

export default api
