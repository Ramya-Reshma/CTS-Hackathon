import axios from 'axios'

const API_BASE_URL = '/api'

// Create axios instance with base URL
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5 minutes for long-running analysis
})

// Request interceptor to attach JWT Authorization Bearer header
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('medlytics_auth_token')
  if (token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor for consistent error extraction
api.interceptors.response.use(
  response => response,
  error => {
    const detail = error.response?.data?.detail
    const message = typeof detail === 'string' ? detail : (error.response?.data?.message || error.message)
    console.error('[API Error]', message, error.response?.status)
    const err = new Error(message)
    err.status = error.response?.status
    err.response = error.response
    throw err
  }
)

/**
 * ========================================================
 * AUTHENTICATION & ACCESS CONTROL APIS
 * ========================================================
 */

export const registerUser = async (data) => {
  const response = await api.post('/auth/register', data)
  return response.data
}

export const loginUser = async (credentials) => {
  const response = await api.post('/auth/login', credentials)
  if (response.data?.access_token) {
    localStorage.setItem('medlytics_auth_token', response.data.access_token)
    localStorage.setItem('medlytics_user', JSON.stringify(response.data.user))
  }
  return response.data
}

export const verifyEmailToken = async (token) => {
  const response = await api.post('/auth/verify-email', { token })
  return response.data
}

export const resendVerificationEmail = async (email) => {
  const response = await api.post(`/auth/resend-verification?email=${encodeURIComponent(email)}`)
  return response.data
}

export const getMe = async () => {
  const response = await api.get('/auth/me')
  return response.data
}

export const getUsers = async (statusFilter) => {
  const params = statusFilter ? `?status_filter=${statusFilter}` : ''
  const response = await api.get(`/auth/users${params}`)
  return response.data
}

export const approveUser = async (userId) => {
  const response = await api.post(`/auth/approve/${userId}`)
  return response.data
}

export const rejectUser = async (userId) => {
  const response = await api.post(`/auth/reject/${userId}`)
  return response.data
}

export const logoutUser = async () => {
  try {
    await api.post('/auth/logout')
  } catch (e) {
    // Ignore network error on logout
  } finally {
    localStorage.removeItem('medlytics_auth_token')
    localStorage.removeItem('medlytics_user')
  }
}

/**
 * ========================================================
 * MONITORING & ANALYSIS APIS
 * ========================================================
 */

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
 * Get authoritative SLA records and findings for a run
 */
export const getSLARecords = async (runId) => {
  const response = await api.get(`/runs/${runId}/sla`)
  return response.data
}

/**
 * Get 4-stage processing integrity for a run
 */
export const getProcessingIntegrity = async (runId) => {
  const response = await api.get(`/runs/${runId}/integrity`)
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
  link.remove()
}

/**
 * Health check
 */
export const healthCheck = async () => {
  const response = await api.get('/health')
  return response.data
}

/**
 * ========================================================
 * AUTO-RESOLUTION AGENT APIS
 * ========================================================
 */

/** Evaluate an issue against the 10-point Decision Gate */
export const evaluateAutoResolution = async (payload) => {
  const response = await api.post('/auto-resolve/evaluate', payload)
  return response.data
}

/** Execute an approved allowlisted remediation action */
export const executeAutoResolution = async (payload) => {
  const response = await api.post('/auto-resolve/execute', payload)
  return response.data
}

/** Retrieve audit history for a run */
export const getAutoResolutionHistory = async (runId) => {
  const response = await api.get('/auto-resolve/history', { params: { run_id: runId, limit: 100 } })
  return response.data
}

/** Retrieve controlled taxonomy and registry */
export const getAutoResolutionRegistry = async () => {
  const response = await api.get('/auto-resolve/registry')
  return response.data
}

