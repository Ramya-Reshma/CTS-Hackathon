import axios from 'axios'

const API_BASE_URL = '/api'

// Create axios instance with base URL
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5 minutes for long-running analysis
})

// Error handler
api.interceptors.response.use(
  response => response,
  error => {
    const message = error.response?.data?.detail || error.response?.data?.message || error.message
    console.error('[API Error]', message)
    throw new Error(message)
  }
)

/**
 * Upload a file and trigger analysis
 */
export const uploadAndAnalyze = async (file) => {
  const formData = new FormData()
  formData.append('file', file)

  const response = await api.post('/analyze', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })

  return response.data
}

/**
 * Get run information
 */
export const getRunInfo = async (runId) => {
  const response = await api.get(`/runs/${runId}`)
  return response.data
}

/**
 * List historical analysis runs
 */
export const getRuns = async (options = {}) => {
  const { page = 1, pageSize = 20 } = options
  const params = new URLSearchParams()
  params.append('page', page)
  params.append('page_size', pageSize)
  const response = await api.get(`/runs?${params}`)
  return response.data
}

/**
 * List anomalies for a run with optional filtering
 */
export const getAnomalies = async (runId, options = {}) => {
  const { severity, page = 1, pageSize = 50, search } = options

  const params = new URLSearchParams()
  params.append('page', page)
  params.append('page_size', pageSize)
  
  if (severity) params.append('severity', severity)
  if (search) params.append('search', search)

  const response = await api.get(`/runs/${runId}/anomalies?${params}`)
  return response.data
}

/**
 * Get detailed information about a single anomaly
 */
export const getAnomalyDetail = async (anomalyId) => {
  const response = await api.get(`/anomalies/${anomalyId}`)
  return response.data
}

/**
 * Download results as CSV
 */
export const downloadResults = async (runId, options = {}) => {
  const { severity, format = 'csv' } = options

  const params = new URLSearchParams()
  params.append('format', format)
  if (severity) params.append('severity', severity)

  const response = await api.get(
    `/runs/${runId}/download?${params}`,
    { responseType: 'blob' }
  )

  // Create download link
  const url = window.URL.createObjectURL(new Blob([response.data]))
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', `anomalies_${runId}.${format}`)
  document.body.appendChild(link)
  link.click()
  link.parentNode.removeChild(link)
  window.URL.revokeObjectURL(url)
}

/**
 * Health check
 */
export const healthCheck = async () => {
  const response = await api.get('/health')
  return response.data
}
