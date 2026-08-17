import React from 'react'
import { useStore } from '../hooks/useStore'
import './Filters.css'

const SearchIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" stroke="currentColor" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
  </svg>
)

const DownloadIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" stroke="currentColor" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
    <polyline points="7 10 12 15 17 10"/>
    <line x1="12" y1="15" x2="12" y2="3"/>
  </svg>
)

export default function Filters({ onDownload, isDownloading }) {
  const severityFilter  = useStore(state => state.severityFilter)
  const setSeverityFilter = useStore(state => state.setSeverityFilter)
  const searchQuery     = useStore(state => state.searchQuery)
  const setSearchQuery  = useStore(state => state.setSearchQuery)

  return (
    <div className="filters-container">
      <div className="filters-left">

        <div className="filter-group">
          <span className="filter-label">Severity</span>
          <div className="filter-buttons">
            <button className={`filter-button${!severityFilter ? ' active' : ''}`}  onClick={() => setSeverityFilter(null)}>All</button>
            <button className={`filter-button high${severityFilter === 'HIGH'   ? ' active' : ''}`} onClick={() => setSeverityFilter('HIGH')}>High</button>
            <button className={`filter-button medium${severityFilter === 'MEDIUM' ? ' active' : ''}`} onClick={() => setSeverityFilter('MEDIUM')}>Medium</button>
            <button className={`filter-button low${severityFilter === 'LOW'    ? ' active' : ''}`} onClick={() => setSeverityFilter('LOW')}>Low</button>
          </div>
        </div>

        <div className="filter-group">
          <span className="filter-label">Search</span>
          <div className="search-wrap">
            <span className="search-icon"><SearchIcon /></span>
            <input
              type="text"
              className="search-input"
              placeholder="Record ID, type, anomaly..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </div>

      </div>

      <div className="filters-right">
        <button className="download-button" onClick={onDownload} disabled={isDownloading} title="Download filtered results as CSV">
          {isDownloading ? (
            <><span className="spinner-sm" /> Downloading...</>
          ) : (
            <><DownloadIcon /> Download Results</>
          )}
        </button>
      </div>
    </div>
  )
}
