import React, { useEffect, useState } from 'react'
import { useStore } from './hooks/useStore'
import { healthCheck } from './services/api'
import Upload from './pages/Upload'
import MedlyticsApp from './pages/MedlyticsApp'
import './App.css'

export default function App() {
  const currentRun = useStore(state => state.currentRun)
  const [apiHealthy, setApiHealthy] = useState(false)
  const [checking, setChecking] = useState(true)

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
        <div className="spinner" />
        <p>Initializing MEDLYTICS...</p>
      </div>
    )
  }

  if (!apiHealthy) {
    return (
      <div className="app-error">
        <div className="error-container">
          <h1>Connection Error</h1>
          <p>Unable to connect to the MEDLYTICS API.</p>
          <p className="text-muted">Make sure the backend is running on http://localhost:8000</p>
        </div>
      </div>
    )
  }

  return (
    <div className="app">
      {!currentRun ? <Upload /> : <MedlyticsApp />}
    </div>
  )
}
