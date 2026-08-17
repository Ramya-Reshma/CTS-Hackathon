import React from 'react'
import './Auth.css'

export default function AuthShell({ children }) {
  return (
    <div className="auth-wrapper">
      {/* Enterprise Header */}
      <header className="auth-topbar">
        <div className="auth-brand">
          <div className="auth-logo-badge">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
            </svg>
          </div>
          <div className="auth-brand-text">
            <h1>MEDLYTICS</h1>
            <p>Healthcare Intelligence &amp; Monitoring Platform</p>
          </div>
        </div>
        <div className="auth-environment-badge">
          ENTERPRISE SECURE ACCESS
        </div>
      </header>

      {/* Main Form/Card Content */}
      <main className="auth-main-container">
        {children}
      </main>

      {/* Enterprise Footer */}
      <footer className="auth-footer">
        MEDLYTICS Healthcare Data Quality &amp; Anomaly Monitoring System &nbsp;·&nbsp; Protected by Enterprise Authentication &amp; RBAC
      </footer>
    </div>
  )
}
