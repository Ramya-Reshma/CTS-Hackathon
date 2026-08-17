import React, { useState, useEffect } from 'react'
import { verifyEmailToken } from '../../services/api'
import AuthShell from './AuthShell'

export default function VerifyEmailPage({ initialToken, onNavigate }) {
  const [token, setToken] = useState(initialToken || '')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [verifiedData, setVerifiedData] = useState(null)

  useEffect(() => {
    // Check URL parameters for token
    const urlParams = new URLSearchParams(window.location.search)
    const urlToken = urlParams.get('token')
    if (urlToken && !initialToken) {
      setToken(urlToken)
      handleVerify(urlToken)
    } else if (initialToken) {
      handleVerify(initialToken)
    }
  }, [])

  const handleVerify = async (tokenToVerify) => {
    const rawToken = tokenToVerify || token
    if (!rawToken || !rawToken.trim()) {
      setError('Please provide a verification token.')
      return
    }

    setLoading(true)
    setError(null)
    try {
      const data = await verifyEmailToken(rawToken.trim())
      setVerifiedData(data)
    } catch (err) {
      setError(err.message || 'Email verification failed or token has expired.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthShell>
      <div className="auth-card">
        {!verifiedData ? (
          <>
            <div className="auth-card-header">
              <h2>Verify Your Email Address</h2>
              <p>Activate your MEDLYTICS account with the secure verification token sent to your email</p>
            </div>

            {error && (
              <div className="auth-alert auth-alert-error" role="alert" style={{ marginBottom: '18px' }}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ flexShrink: 0, marginTop: '2px' }}>
                  <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
                </svg>
                <span>{error}</span>
              </div>
            )}

            <form className="auth-form" onSubmit={(e) => { e.preventDefault(); handleVerify(); }}>
              <div className="auth-field-group">
                <label htmlFor="verify-token-input">Verification Token / Code</label>
                <input
                  id="verify-token-input"
                  type="text"
                  className="auth-input"
                  placeholder="Paste your verification token"
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  required
                />
              </div>

              <button
                type="submit"
                className="auth-submit-btn"
                disabled={loading}
                id="btn-verify-token"
              >
                {loading ? (
                  <>
                    <span className="spinner-sm" />
                    <span>Verifying Token...</span>
                  </>
                ) : (
                  <span>Verify Email Address</span>
                )}
              </button>
            </form>

            <div className="auth-card-footer">
              <p>
                Need to sign in?{' '}
                <button
                  type="button"
                  className="auth-link"
                  onClick={() => onNavigate('login')}
                  style={{ fontWeight: 600 }}
                >
                  Return to Sign In
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
            <h2 className="auth-status-title">EMAIL VERIFIED</h2>
            <p className="auth-status-desc">
              Your email address has been successfully verified.
              <br />
              <strong style={{ color: '#f59e0b' }}>Your account is now awaiting administrator approval.</strong>
            </p>

            <div className="auth-status-badge-box">
              <div className="auth-status-row">
                <span className="label">Email Verified:</span>
                <span className="val" style={{ color: '#10b981' }}>✓ TRUE</span>
              </div>
              <div className="auth-status-row">
                <span className="label">Account Approved:</span>
                <span className="val" style={{ color: '#f59e0b' }}>FALSE (Pending Review)</span>
              </div>
              <div className="auth-status-row">
                <span className="label">Status:</span>
                <span className="val" style={{ color: '#f59e0b' }}>PENDING_APPROVAL</span>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', width: '100%' }}>
              <button
                type="button"
                className="auth-submit-btn"
                onClick={() => onNavigate('pending-approval', { email: verifiedData.email })}
              >
                View Account Status
              </button>
              <button
                type="button"
                className="auth-secondary-btn"
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
