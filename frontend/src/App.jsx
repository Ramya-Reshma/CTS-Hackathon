import React, { useEffect, useState } from 'react'
import { useStore } from './hooks/useStore'
import { healthCheck, getMe, logoutUser } from './services/api'
import LoginPage from './pages/Auth/LoginPage'
import RegisterPage from './pages/Auth/RegisterPage'
import VerifyEmailPage from './pages/Auth/VerifyEmailPage'
import PendingApprovalPage from './pages/Auth/PendingApprovalPage'
import MedlyticsApp from './pages/MedlyticsApp'
import './App.css'

export default function App() {
  const currentRun = useStore(state => state.currentRun)
  const setCurrentRun = useStore(state => state.setCurrentRun)
  const resetStore = useStore(state => state.reset)

  const [apiHealthy, setApiHealthy] = useState(false)
  const [checking, setChecking] = useState(true)
  const [user, setUser] = useState(null)
  const [authView, setAuthView] = useState('login') // 'login', 'register', 'verify-email', 'pending-approval'
  const [authContext, setAuthContext] = useState({})
  const [initialPage, setInitialPage] = useState('uploads')

  // Check URL query parameters for direct verification links (e.g. /verify-email?token=...)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const token = params.get('token')
    if (token) {
      setAuthView('verify-email')
      setAuthContext({ token })
    }
  }, [])

  // Initialize and verify authentication
  useEffect(() => {
    const initApp = async () => {
      try {
        await healthCheck()
        setApiHealthy(true)

        // Verify stored session token
        const token = localStorage.getItem('medlytics_auth_token')
        if (token) {
          try {
            const userData = await getMe()
            if (userData && userData.approval_status === 'APPROVED') {
              setUser(userData)
              // DO NOT auto-load last run — user must upload or select explicitly
              setInitialPage('uploads')
            } else if (userData && userData.approval_status === 'PENDING_APPROVAL') {
              setAuthView('pending-approval')
              setAuthContext({ email: userData.email })
            } else {
              localStorage.removeItem('medlytics_auth_token')
              setUser(null)
            }
          } catch (err) {
            console.warn('Session verification failed, requiring login:', err)
            localStorage.removeItem('medlytics_auth_token')
            setUser(null)
          }
        }
      } catch (error) {
        console.error('API health check failed:', error)
        setApiHealthy(false)
      } finally {
        setChecking(false)
      }
    }

    initApp()
  }, [])

  const handleLoginSuccess = (authenticatedUser) => {
    // Always start fresh — send user to Uploads page, no stale data
    setInitialPage('uploads')
    setUser(authenticatedUser)
  }

  const handleLogout = async () => {
    await logoutUser()
    setUser(null)
    setAuthView('login')
    resetStore()
  }

  const handleNavigateAuth = (view, context = {}) => {
    setAuthView(view)
    setAuthContext(context)
  }

  if (checking) {
    return (
      <div className="app-loading">
        <div className="spinner" />
        <p>Initializing MEDLYTICS Healthcare Intelligence Platform...</p>
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

  // If user is authenticated and approved, render the MEDLYTICS Dashboard
  if (user && user.approval_status === 'APPROVED') {
    return (
      <div className="app">
        <MedlyticsApp user={user} onLogout={handleLogout} initialPage={initialPage} />
      </div>
    )
  }

  // Otherwise, render authentication pages (Login, Register, Verify Email, Pending Approval)
  switch (authView) {
    case 'register':
      return (
        <RegisterPage
          onNavigate={handleNavigateAuth}
          onRegistered={(email) => setAuthContext({ email })}
        />
      )
    case 'verify-email':
      return (
        <VerifyEmailPage
          initialToken={authContext.token}
          onNavigate={handleNavigateAuth}
        />
      )
    case 'pending-approval':
      return (
        <PendingApprovalPage
          email={authContext.email}
          onNavigate={handleNavigateAuth}
        />
      )
    case 'login':
    default:
      return (
        <LoginPage
          onNavigate={handleNavigateAuth}
          onLoginSuccess={handleLoginSuccess}
        />
      )
  }
}
