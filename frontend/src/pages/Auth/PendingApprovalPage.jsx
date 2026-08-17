import React, { useState } from 'react'
import { approveUser, getUsers } from '../../services/api'
import AuthShell from './AuthShell'

export default function PendingApprovalPage({ email, onNavigate }) {
  const [adminMode, setAdminMode] = useState(false)
  const [pendingUsers, setPendingUsers] = useState([])
  const [loading, setLoading] = useState(false)
  const [actionMessage, setActionMessage] = useState(null)

  const handleFetchPending = async () => {
    setLoading(true)
    try {
      const users = await getUsers('PENDING_APPROVAL')
      setPendingUsers(users)
    } catch (err) {
      console.warn('Could not fetch pending users:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleApprove = async (userId) => {
    try {
      const res = await approveUser(userId)
      setActionMessage(res.message || 'User approved successfully.')
      handleFetchPending()
    } catch (err) {
      setActionMessage(err.message || 'Approval failed.')
    }
  }

  return (
    <AuthShell>
      <div className="auth-card">
        <div className="auth-status-container">
          <div className="auth-status-icon-wrap pending">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
            </svg>
          </div>
          <h2 className="auth-status-title">Account Pending Approval</h2>
          <p className="auth-status-desc">
            Your email address is verified. Your MEDLYTICS account is currently undergoing organizational approval.
          </p>

          <div className="auth-status-badge-box">
            <div className="auth-status-row">
              <span className="label">Account Status:</span>
              <span className="val" style={{ color: '#f59e0b' }}>PENDING_APPROVAL</span>
            </div>
            <div className="auth-status-row">
              <span className="label">Email Verified:</span>
              <span className="val" style={{ color: '#10b981' }}>✓ TRUE</span>
            </div>
            <div className="auth-status-row">
              <span className="label">Dashboard Access:</span>
              <span className="val" style={{ color: '#ef4444' }}>Restricted until approved</span>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', width: '100%' }}>
            <button
              type="button"
              className="auth-submit-btn"
              onClick={() => onNavigate('login')}
            >
              Sign In with Approved Account
            </button>

            {/* Administrative / Demo Helper Drawer */}
            <div style={{ marginTop: '14px', paddingTop: '14px', borderTop: '1px solid rgba(255,255,255,0.08)', width: '100%' }}>
              <button
                type="button"
                className="auth-link"
                style={{ fontSize: '11px', color: '#94a3b8' }}
                onClick={() => {
                  setAdminMode(prev => !prev)
                  if (!adminMode) handleFetchPending()
                }}
              >
                {adminMode ? '▲ Hide Administrator Review Panel' : '▼ Administrator Account Review (Admin Console)'}
              </button>

              {adminMode && (
                <div style={{ marginTop: '12px', background: 'rgba(15,23,42,0.9)', padding: '12px', borderRadius: '6px', textAlign: 'left' }}>
                  <div style={{ fontSize: '12px', fontWeight: 600, color: '#38bdf8', marginBottom: '8px' }}>
                    Pending Approvals Queue
                  </div>
                  {actionMessage && (
                    <div style={{ fontSize: '11px', color: '#10b981', marginBottom: '8px' }}>{actionMessage}</div>
                  )}
                  {loading ? (
                    <div style={{ fontSize: '11px', color: '#94a3b8' }}>Loading accounts...</div>
                  ) : pendingUsers.length === 0 ? (
                    <div style={{ fontSize: '11px', color: '#94a3b8' }}>No accounts currently pending approval.</div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {pendingUsers.map(u => (
                        <div key={u.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '11px', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '6px' }}>
                          <div>
                            <div style={{ fontWeight: 600, color: '#fff' }}>{u.name}</div>
                            <div style={{ color: '#94a3b8' }}>{u.email}</div>
                          </div>
                          <button
                            type="button"
                            onClick={() => handleApprove(u.id)}
                            style={{ background: '#10b981', border: 'none', color: '#fff', padding: '4px 8px', borderRadius: '4px', cursor: 'pointer', fontSize: '10px', fontWeight: 600 }}
                          >
                            Approve User
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </AuthShell>
  )
}
