import React, { useState } from 'react'
import { registerUser } from '../../services/api'
import AuthShell from './AuthShell'

export default function RegisterPage({ onNavigate, onRegistered }) {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [successData, setSuccessData] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)

    if (!name.trim()) {
      setError('Full Name is required.')
      return
    }
    if (!email.trim()) {
      setError('Email Address is required.')
      return
    }
    if (!password) {
      setError('Password is required.')
      return
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters long.')
      return
    }
    if (password !== confirmPassword) {
      setError('Password and Confirm Password do not match.')
      return
    }

    setLoading(true)
    try {
      const data = await registerUser({
        name: name.trim(),
        email: email.trim().toLowerCase(),
        password,
        confirm_password: confirmPassword,
      })
      setSuccessData({
        email: email.trim(),
        message: data.message || 'Account created successfully. Please check your email to verify your MEDLYTICS account.',
      })
      if (onRegistered) onRegistered(email.trim())
    } catch (err) {
      setError(err.message || 'Registration failed. Please check the provided information.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthShell>
      <div className="auth-card">
        {!successData ? (
          <>
            <div className="auth-card-header">
              <h2>CREATE YOUR MEDLYTICS ACCOUNT</h2>
              <p>Register with your organizational email address to request platform access</p>
            </div>

            {error && (
              <div className="auth-alert auth-alert-error" role="alert" style={{ marginBottom: '18px' }}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ flexShrink: 0, marginTop: '2px' }}>
                  <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
                </svg>
                <span>{error}</span>
              </div>
            )}

            <form className="auth-form" onSubmit={handleSubmit}>
              <div className="auth-field-group">
                <label htmlFor="reg-name">Full Name</label>
                <input
                  id="reg-name"
                  type="text"
                  className="auth-input"
                  placeholder="e.g. Dr. Ramya Reshma"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                />
              </div>

              <div className="auth-field-group">
                <label htmlFor="reg-email">Email Address</label>
                <input
                  id="reg-email"
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
                <label htmlFor="reg-password">Password</label>
                <input
                  id="reg-password"
                  type="password"
                  className="auth-input"
                  placeholder="Minimum 8 characters"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="new-password"
                  required
                />
              </div>

              <div className="auth-field-group">
                <label htmlFor="reg-confirm-password">Confirm Password</label>
                <input
                  id="reg-confirm-password"
                  type="password"
                  className="auth-input"
                  placeholder="Re-enter password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  autoComplete="new-password"
                  required
                />
              </div>

              <button
                type="submit"
                className="auth-submit-btn"
                disabled={loading}
                id="btn-register-submit"
              >
                {loading ? (
                  <>
                    <span className="spinner-sm" />
                    <span>Creating Account...</span>
                  </>
                ) : (
                  <span>Create Account</span>
                )}
              </button>
            </form>

            <div className="auth-card-footer">
              <p>
                Already have a MEDLYTICS account?{' '}
                <button
                  type="button"
                  className="auth-link"
                  onClick={() => onNavigate('login')}
                  style={{ fontWeight: 600 }}
                >
                  Sign In
                </button>
              </p>
            </div>
          </>
        ) : (
          <div className="auth-status-container">
            <div className="auth-status-icon-wrap success">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
              </svg>
            </div>
            <h2 className="auth-status-title">Account Created Successfully</h2>
            <p className="auth-status-desc">
              Your MEDLYTICS account has been created. A verification link has been sent to:
              <br />
              <strong style={{ color: '#38bdf8' }}>{successData.email}</strong>
            </p>

            <div className="auth-status-badge-box">
              <div className="auth-status-row">
                <span className="label">Status:</span>
                <span className="val" style={{ color: '#f59e0b' }}>PENDING_EMAIL_VERIFICATION</span>
              </div>
              <div className="auth-status-row">
                <span className="label">Email Verification:</span>
                <span className="val" style={{ color: '#ef4444' }}>Required</span>
              </div>
              <div className="auth-status-row">
                <span className="label">Account Approval:</span>
                <span className="val" style={{ color: '#94a3b8' }}>Awaiting Verification</span>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', width: '100%' }}>
              <button
                type="button"
                className="auth-secondary-btn"
                onClick={() => onNavigate('verify-email', { email: successData.email })}
              >
                Enter Verification Token / Link
              </button>
              <button
                type="button"
                className="auth-submit-btn"
                onClick={() => onNavigate('login')}
              >
                Return to Sign In
              </button>
            </div>
          </div>
        )}
      </div>
    </AuthShell>
  )
}
