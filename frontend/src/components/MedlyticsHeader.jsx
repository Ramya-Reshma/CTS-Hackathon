import React from 'react'
import { useStore } from '../hooks/useStore'
import { NAV_PAGES } from '../pages/MedlyticsApp'
import MedlyticsLogo from './MedlyticsLogo'
import './MedlyticsHeader.css'

const MenuIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" stroke="currentColor" fill="none" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
    <line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/>
  </svg>
)

export default function MedlyticsHeader({ activePage, onMenuClick }) {
  const currentRun = useStore(state => state.currentRun)
  const page = NAV_PAGES.find(p => p.id === activePage)

  return (
    <header className="medlytics-topbar">
      <div className="topbar-left">
        <button className="topbar-menu-btn" onClick={onMenuClick} aria-label="Toggle navigation">
          <MenuIcon />
        </button>
        <span className="topbar-page-title">{page?.label || 'Overview'}</span>
      </div>
      <div className="topbar-right">
        {currentRun && (
          <>
            <span className="topbar-run-label">RUN</span>
            <span className="topbar-run-id">{currentRun.run_id}</span>
            <span className="topbar-sep">·</span>
            <span className="topbar-filename" title={currentRun.filename}>{currentRun.filename}</span>
          </>
        )}
        <div style={{ marginLeft: '12px', paddingLeft: '12px', borderLeft: '1px solid var(--border-light)' }}>
          <MedlyticsLogo size={20} textColor="var(--navy-900)" showText={true} />
        </div>
      </div>
    </header>
  )
}

