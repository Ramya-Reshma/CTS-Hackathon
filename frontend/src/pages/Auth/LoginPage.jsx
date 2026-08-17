import React, { useState } from 'react'
import { loginUser, resendVerificationEmail } from '../../services/api'
import AuthShell from './AuthShell'

export default function LoginPage({ onNavigate, onLoginSuccess }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [infoMessage, setInfoMessage] = useState(null)
  const [showResend, setShowResend] = useState(false)
  const [resending, setResending] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setInfoMessage(null)
    setShowResend(false)

    if (!email || !password) {
      setError('Please provide both Email Address and Password.')
      return
    }

    setLoading(true)
    try {
      const data = await loginUser({ email: email.trim(), password })
      if (data?.access_token) {
        onLoginSuccess(data.user)
      }
    } catch (err) {
      const msg = err.message || 'Login failed.'
      setError(msg)
      if (msg.toLowerCase().includes('verify your email')) {
        setShowResend(true)
      }
    } finally {
      setLoading(false)
    }
  }

  const handleResend = async () => {
    if (!email) return
    setResending(true)
    setError(null)
    try {
      const res = await resendVerificationEmail(email.trim())
      setInfoMessage(res.message || 'Verification link has been sent.')
      setShowResend(false)
    } catch (err) {
      setError(err.message || 'Failed to resend verification link.')
    } finally {
      setResending(false)
    }
  }

  return (
    <AuthShell>
      <div className="auth-card">
        <div className="auth-card-header">
          <h2>Sign In to MEDLYTICS</h2>
          <p>Enter your credentials to access healthcare anomaly &amp; SLA monitoring</p>
        </div>

        {error && (
          <div className="auth-alert auth-alert-error" role="alert" style={{ marginBottom: '18px' }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ flexShrink: 0, marginTop: '2px' }}>
              <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            <div>
              <span>{error}</span>
              {showResend && (
                <div style={{ marginTop: '8px' }}>
                  <button
                    type="button"
                    className="auth-link"
                    onClick={handleResend}
                    disabled={resending}
                    style={{ fontWeight: 600, textDecoration: 'underline' }}
                  >
                    {resending ? 'Sending link...' : 'Click here to resend verification email'}
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

        {infoMessage && (
          <div className="auth-alert auth-alert-success" role="alert" style={{ marginBottom: '18px' }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ flexShrink: 0, marginTop: '2px' }}>
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
            </svg>
            <span>{infoMessage}</span>
          </div>
        )}

        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="auth-field-group">
            <label htmlFor="login-email">Email Address</label>
            <input
              id="login-email"
              type="email"
              className="auth-input"
              placeholder="e.g. ramya@medlytics.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
            />
          </div>

          <div className="auth-field-group">
            <div className="auth-helper-row">
              <label htmlFor="login-password">Password</label>
              <button
                type="button"
                className="auth-link"
                onClick={() => alert('Please contact your MEDLYTICS platform administrator to reset your enterprise password.')}
              >
                Forgot Password?
              </button>
            </div>
            <input
              id="login-password"
              type="password"
              className="auth-input"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </div>

          <button
            type="submit"
            className="auth-submit-btn"
            disabled={loading}
            id="btn-sign-in"
          >
            {loading ? (
              <>
                <span className="spinner-sm" />
                <span>Signing In...</span>
              </>
            ) : (
              <span>Sign In</span>
            )}
          </button>
        </form>

        <div className="auth-card-footer">
          <p>
            Don't have a MEDLYTICS account?{' '}
            <button
              type="button"
              className="auth-link"
              onClick={() => onNavigate('register')}
              style={{ fontWeight: 600 }}
              id="btn-goto-register"
            >
              Create Account
            </button>
          </p>
        </div>
      </div>
    </AuthShell>
  )
}
