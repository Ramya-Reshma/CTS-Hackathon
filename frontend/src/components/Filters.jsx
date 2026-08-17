import React from 'react'
import { useStore } from '../hooks/useStore'
import './Filters.css'

export default function Filters({ onDownload, isDownloading }) {
  const severityFilter = useStore(state => state.severityFilter)
  const setSeverityFilter = useStore(state => state.setSeverityFilter)
  const searchQuery = useStore(state => state.searchQuery)
  const setSearchQuery = useStore(state => state.setSearchQuery)

  return (
    <div className="filters-container">
      <div className="filters-left">
        <div className="filter-group">
          <label className="filter-label">Severity:</label>
          <div className="filter-buttons">
            <button
              className={`filter-button ${!severityFilter ? 'active' : ''}`}
              onClick={() => setSeverityFilter(null)}
            >
              All
            </button>
            <button
              className={`filter-button high ${severityFilter === 'HIGH' ? 'active' : ''}`}
              onClick={() => setSeverityFilter('HIGH')}
            >
              High
            </button>
            <button
              className={`filter-button medium ${severityFilter === 'MEDIUM' ? 'active' : ''}`}
              onClick={() => setSeverityFilter('MEDIUM')}
            >
              Medium
            </button>
            <button
              className={`filter-button low ${severityFilter === 'LOW' ? 'active' : ''}`}
              onClick={() => setSeverityFilter('LOW')}
            >
              Low
            </button>
          </div>
        </div>

        <div className="filter-group">
          <label className="filter-label">Search:</label>
          <input
            type="text"
            className="search-input"
            placeholder="Record ID, type, anomaly..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      <div className="filters-right">
        <button
          className="download-button"
          onClick={onDownload}
          disabled={isDownloading}
          title="Download filtered results as CSV"
        >
          {isDownloading ? (
            <>
              <span className="spinner-small"></span>
              Downloading...
            </>
          ) : (
            <>
              📥 Download Results
            </>
          )}
        </button>
      </div>
    </div>
  )
}
