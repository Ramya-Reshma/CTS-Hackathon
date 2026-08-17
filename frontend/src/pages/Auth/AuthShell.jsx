import React from 'react'
import MedlyticsLogo from '../../components/MedlyticsLogo'
import './Auth.css'

export default function AuthShell({ children }) {
  return (
    <div className="auth-wrapper">
      {/* Enterprise Header */}
      <header className="auth-topbar">
        <div className="auth-brand">
          <MedlyticsLogo size={32} showText={true} textColor="#f8fafc" />
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
