import React, { useEffect, useState } from 'react'
import { useStore } from './hooks/useStore'
import { healthCheck } from './services/api'
import Upload from './pages/Upload'
import Dashboard from './pages/Dashboard'
import './App.css'

export default function App() {
  const currentRun = useStore(state => state.currentRun)
  const [apiHealthy, setApiHealthy] = useState(false)
  const [checking, setChecking] = useState(true)

  // Check API health on mount
  useEffect(() => {
    const checkHealth = async () => {
      try {
        await healthCheck()
        setApiHealthy(true)
      } catch (error) {
        console.error('API health check failed:', error)
        setApiHealthy(false)
      } finally {
        setChecking(false)
      }
    }

    checkHealth()
  }, [])

  if (checking) {
    return (
      <div className="app-loading">
        <div className="spinner"></div>
        <p>Initializing UC10 Anomaly Monitor...</p>
      </div>
    )
  }

  if (!apiHealthy) {
    return (
      <div className="app-error">
        <div className="error-container">
          <h1>Connection Error</h1>
          <p>Unable to connect to UC10 API.</p>
          <p className="text-muted">Make sure the backend is running on http://localhost:8000</p>
        </div>
      </div>
    )
  }

  return (
    <div className="app">
      {!currentRun ? <Upload /> : <Dashboard />}
    </div>
  )
}
