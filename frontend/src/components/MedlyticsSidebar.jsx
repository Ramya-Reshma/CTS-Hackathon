import React from 'react'
import { NAV_PAGES } from '../pages/MedlyticsApp'
import './MedlyticsSidebar.css'

// Inline SVG icons
const icons = {
  overview: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
      <rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>
    </svg>
  ),
  anomaly: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
    </svg>
  ),
  sla: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
    </svg>
  ),
  quality: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
    </svg>
  ),
  recommendation: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z"/>
    </svg>
  ),
  uploads: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
      <polyline points="17 8 12 3 7 8"/>
      <line x1="12" y1="3" x2="12" y2="15"/>
    </svg>
  ),
}

export default function MedlyticsSidebar({ activePage, onNavigate, open, onClose, user, onLogout }) {
  return (
    <>
      {/* Mobile overlay */}
      {open && <div className="sidebar-overlay" onClick={onClose} />}

      <aside className={`medlytics-sidebar${open ? ' open' : ''}`}>
        {/* Brand */}
        <div className="sidebar-brand">
          <div className="sidebar-logo">
            <span className="sidebar-logo-m">M</span>
          </div>
          <div className="sidebar-brand-text">
            <span className="sidebar-product-name">MEDLYTICS</span>
            <span className="sidebar-product-sub">Healthcare Intelligence</span>
          </div>
        </div>

        <div className="sidebar-divider" />

        {/* Navigation */}
        <nav className="sidebar-nav" role="navigation" aria-label="Main navigation">
          {NAV_PAGES.map(page => (
            <button
              key={page.id}
              className={`sidebar-nav-item${activePage === page.id ? ' active' : ''}`}
              onClick={() => onNavigate(page.id)}
              aria-current={activePage === page.id ? 'page' : undefined}
            >
              <span className="sidebar-nav-icon">{icons[page.icon]}</span>
              <span className="sidebar-nav-label">{page.label}</span>
              {activePage === page.id && <span className="sidebar-active-bar" />}
            </button>
          ))}
        </nav>

        <div className="sidebar-footer" style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {user && (
            <div style={{
              background: 'rgba(15, 23, 42, 0.65)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              borderRadius: '8px',
              padding: '8px 10px',
              fontSize: '11px',
              textAlign: 'left',
              width: '100%',
              boxSizing: 'border-box',
            }}>
              <div style={{ fontWeight: 600, color: '#f8fafc', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {user.name || 'Enterprise User'}
              </div>
              <div style={{ color: '#64748b', fontSize: '10px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {user.email}
              </div>
            </div>
          )}

          <button
            type="button"
            onClick={onLogout}
            style={{
              width: '100%',
              padding: '8px 12px',
              background: 'rgba(239, 68, 68, 0.12)',
              border: '1px solid rgba(239, 68, 68, 0.25)',
              borderRadius: '6px',
              color: '#fca5a5',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              transition: 'all 0.2s ease',
            }}
            id="btn-sidebar-logout"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
              <polyline points="16 17 21 12 16 7"/>
              <line x1="21" y1="12" x2="9" y2="12"/>
            </svg>
            <span>Sign Out</span>
          </button>

          <span className="sidebar-footer-text">MEDLYTICS · v2.0 Enterprise</span>
        </div>
      </aside>
    </>
  )
}
