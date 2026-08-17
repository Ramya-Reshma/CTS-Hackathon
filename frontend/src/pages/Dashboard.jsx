import React, { useEffect, useState } from 'react'
import { useStore } from '../hooks/useStore'
import { getAnomalies, getRunInfo, downloadResults } from '../services/api'
import SummaryCards from '../components/SummaryCards'
import AnomaliesTable from '../components/AnomaliesTable'
import AnomalyDetail from '../components/AnomalyDetail'
import Filters from '../components/Filters'
import './Dashboard.css'

// ── Tiny SVG icons (presentation only) ──────────────────────
const SearchIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" stroke="currentColor" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
  </svg>
)

export default function Dashboard() {
  const currentRun       = useStore(state => state.currentRun)
  const anomalies        = useStore(state => state.anomalies)
  const setAnomalies     = useStore(state => state.setAnomalies)
  const page             = useStore(state => state.page)
  const setPage          = useStore(state => state.setPage)
  const pageSize         = useStore(state => state.pageSize)
  const totalAnomalies   = useStore(state => state.totalAnomalies)
  const setTotalAnomalies= useStore(state => state.setTotalAnomalies)
  const severityFilter   = useStore(state => state.severityFilter)
  const searchQuery      = useStore(state => state.searchQuery)
  const isLoading        = useStore(state => state.isLoading)
  const setIsLoading     = useStore(state => state.setIsLoading)
  const error            = useStore(state => state.error)
  const setError         = useStore(state => state.setError)
  const selectedAnomaly  = useStore(state => state.selectedAnomaly)
  const setSelectedAnomaly = useStore(state => state.setSelectedAnomaly)
  const statistics       = useStore(state => state.statistics)
  const setStatistics    = useStore(state => state.setStatistics)

  const [isDownloading, setIsDownloading] = useState(false)

  // Load anomalies when run or filters change
  useEffect(() => {
    const loadAnomalies = async () => {
      if (!currentRun) return
      setIsLoading(true)
      setError(null)
      try {
        const result = await getAnomalies(currentRun.run_id, { severity: severityFilter, page, pageSize, search: searchQuery })
        setAnomalies(result.records)
        setTotalAnomalies(result.total)
      } catch (err) {
        setError(err.message || 'Failed to load anomalies')
      } finally {
        setIsLoading(false)
      }
    }
    loadAnomalies()
  }, [currentRun, severityFilter, page, searchQuery])

  // Load run info / statistics on mount
  useEffect(() => {
    const loadRunInfo = async () => {
      if (!currentRun) return
      try {
        const runInfo = await getRunInfo(currentRun.run_id)
        setStatistics(runInfo.statistics)
      } catch (err) {
        console.error('Failed to load run info:', err)
      }
    }
    loadRunInfo()
  }, [currentRun])

  const handleDownload = async () => {
    if (!currentRun) return
    setIsDownloading(true)
    try {
      await downloadResults(currentRun.run_id, { severity: severityFilter, format: 'csv' })
    } catch (err) {
      setError(err.message || 'Failed to download results')
    } finally {
      setIsDownloading(false)
    }
  }

  if (!currentRun) return <div>Loading...</div>

  // ── Derived presentation values ─────────────────────────
  const sev = currentRun.severity_summary || {}
  const total = (sev.high || 0) + (sev.medium || 0) + (sev.low || 0)
  const pct = (n) => total > 0 ? Math.round((n / total) * 100) : 0

  const dqScore = statistics?.overall_data_quality_score

  return (
    <div className="dashboard">

      {/* ── Header ──────────────────────────────────────────── */}
      <header className="dashboard-header">
        <div className="header-brand">
          <span className="header-uc10">UC10</span>
          <span className="header-divider" />
          <span className="header-app-title">Claims &amp; Authorization Anomaly Monitor</span>
        </div>

        <div className="header-run-info">
          <span className="header-run-label">Run</span>
          <span className="header-run-id">{currentRun.run_id}</span>
          <span className="header-filename" title={currentRun.filename}>{currentRun.filename}</span>
          <span className="header-status-badge">
            <span className="header-status-dot" />
            Analysis Complete
          </span>
        </div>
      </header>

      <div className="dashboard-body">

        {/* ── SECTION 1: Executive Overview ───────────────────── */}
        <section>
          <div className="section-header">
            <span className="section-title">Executive Overview</span>
            <span className="section-header-line" />
          </div>
          <SummaryCards
            totalRecords={currentRun.total_records}
            totalAnomalies={currentRun.total_anomalies}
            severitySummary={currentRun.severity_summary}
            overallDataQualityScore={statistics?.overall_data_quality_score}
          />
        </section>

        {/* ── SECTION 2: Monitoring Overview ──────────────────── */}
        <section>
          <div className="section-header">
            <span className="section-title">Monitoring Overview</span>
            <span className="section-header-line" />
          </div>
          <div className="monitoring-grid">

            {/* Anomaly distribution bar chart */}
            <div className="monitor-card">
              <div className="monitor-card-title">Anomaly Distribution by Severity</div>
              {[
                { key: 'high',   label: 'High',   cls: 'high',   count: sev.high   || 0 },
                { key: 'medium', label: 'Medium', cls: 'medium', count: sev.medium || 0 },
                { key: 'low',    label: 'Low',    cls: 'low',    count: sev.low    || 0 },
              ].map(row => (
                <div className="dist-row" key={row.key}>
                  <span className="dist-label">{row.label}</span>
                  <div className="dist-bar-bg">
                    <div className={`dist-bar-fill ${row.cls}`} style={{ width: `${pct(row.count)}%` }} />
                  </div>
                  <span className="dist-count">{row.count.toLocaleString()}</span>
                </div>
              ))}
            </div>

            {/* Correlation signals — powered by existing backend fields */}
            <div className="monitor-card">
              <div className="monitor-card-title">Correlation Signals</div>
              {anomalies.length > 0 ? (
                <div className="corr-signals">
                  {(() => {
                    const corrCount = anomalies.filter(a => a.correlation_anomaly).length
                    const qsCount   = anomalies.filter(a => a.quantity_supply_anomaly).length
                    return (
                      <>
                        <div className="corr-signal-row">
                          <span className="corr-signal-label">Paid_Amount</span>
                          <span className="corr-arrow">↔</span>
                          <span className="corr-signal-label">Allowed_Amount</span>
                          {corrCount > 0 && <span className="corr-signal-count">{corrCount} flagged</span>}
                        </div>
                        <div className="corr-signal-row">
                          <span className="corr-signal-label">Quantity_Dispensed</span>
                          <span className="corr-arrow">↔</span>
                          <span className="corr-signal-label">Days_Supply</span>
                          {qsCount > 0 && <span className="corr-signal-count">{qsCount} flagged</span>}
                        </div>
                      </>
                    )
                  })()}
                </div>
              ) : (
                <p className="corr-unavail">Load anomalies to see correlation signals.</p>
              )}
            </div>

            {/* Data Quality */}
            {dqScore != null && (
              <div className="monitor-card">
                <div className="monitor-card-title">Data Quality Score</div>
                <div className="dq-score-row">
                  <span className="dq-score-big">{Number(dqScore).toFixed(1)}</span>
                  <span className="dq-score-denom">/ 100</span>
                </div>
                <div className="dq-bar-bg">
                  <div className="dq-bar-fill" style={{ width: `${Math.min(dqScore, 100)}%` }} />
                </div>
                <span className="dq-bar-label">Overall dataset quality</span>
              </div>
            )}

          </div>
        </section>

        {/* ── SECTION 3: Anomaly Intelligence ─────────────────── */}
        <section>
          <div className="section-header">
            <span className="section-title">Anomaly Intelligence</span>
            <span className="section-header-line" />
          </div>

          <Filters onDownload={handleDownload} isDownloading={isDownloading} />

          {error && (
            <div className="error-banner" role="alert">
              <svg width="16" height="16" viewBox="0 0 24 24" stroke="currentColor" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
              </svg>
              {error}
            </div>
          )}

          {isLoading ? (
            <div className="loading-container">
              <div className="spinner" />
              <p className="loading-text">Loading anomalies...</p>
            </div>
          ) : anomalies.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon"><SearchIcon /></div>
              <h3>No anomalies found</h3>
              <p>Try adjusting your filters or search criteria</p>
            </div>
          ) : (
            <>
              <AnomaliesTable anomalies={anomalies} onSelectAnomaly={setSelectedAnomaly} />

              <div className="pagination">
                <button
                  disabled={page === 1}
                  onClick={() => setPage(page - 1)}
                  className="pagination-button"
                >
                  ← Previous
                </button>
                <span className="pagination-info">
                  Page {page} of {Math.ceil(totalAnomalies / pageSize)}
                  <span className="text-muted">· {totalAnomalies.toLocaleString()} anomalies</span>
                </span>
                <button
                  disabled={page >= Math.ceil(totalAnomalies / pageSize)}
                  onClick={() => setPage(page + 1)}
                  className="pagination-button"
                >
                  Next →
                </button>
              </div>
            </>
          )}
        </section>

      </div>

      {/* ── Detail Modal ─────────────────────────────────────── */}
      {selectedAnomaly && (
        <AnomalyDetail anomaly={selectedAnomaly} onClose={() => setSelectedAnomaly(null)} />
      )}
    </div>
  )
}
