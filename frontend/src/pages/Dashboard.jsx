import React, { useEffect, useState } from 'react'
import { useStore } from '../hooks/useStore'
import { getAnomalies, getRunInfo, downloadResults } from '../services/api'
import SummaryCards from '../components/SummaryCards'
import AnomaliesTable from '../components/AnomaliesTable'
import AnomalyDetail from '../components/AnomalyDetail'
import Filters from '../components/Filters'
import './Dashboard.css'

export default function Dashboard() {
  const currentRun = useStore(state => state.currentRun)
  const anomalies = useStore(state => state.anomalies)
  const setAnomalies = useStore(state => state.setAnomalies)
  const page = useStore(state => state.page)
  const setPage = useStore(state => state.setPage)
  const pageSize = useStore(state => state.pageSize)
  const totalAnomalies = useStore(state => state.totalAnomalies)
  const setTotalAnomalies = useStore(state => state.setTotalAnomalies)
  const severityFilter = useStore(state => state.severityFilter)
  const searchQuery = useStore(state => state.searchQuery)
  const isLoading = useStore(state => state.isLoading)
  const setIsLoading = useStore(state => state.setIsLoading)
  const error = useStore(state => state.error)
  const setError = useStore(state => state.setError)
  const selectedAnomaly = useStore(state => state.selectedAnomaly)
  const setSelectedAnomaly = useStore(state => state.setSelectedAnomaly)
  const statistics = useStore(state => state.statistics)
  const setStatistics = useStore(state => state.setStatistics)

  const [isDownloading, setIsDownloading] = useState(false)

  // Load anomalies when run or filters change
  useEffect(() => {
    const loadAnomalies = async () => {
      if (!currentRun) return

      setIsLoading(true)
      setError(null)

      try {
        const result = await getAnomalies(currentRun.run_id, {
          severity: severityFilter,
          page,
          pageSize,
          search: searchQuery,
        })

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

  // Load run info and statistics on mount
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
      await downloadResults(currentRun.run_id, {
        severity: severityFilter,
        format: 'csv',
      })
    } catch (err) {
      setError(err.message || 'Failed to download results')
    } finally {
      setIsDownloading(false)
    }
  }

  if (!currentRun) {
    return <div>Loading...</div>
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <div className="header-content">
          <h1>UC10 Anomaly Monitor</h1>
          <p className="run-info">
            Analysis: <span className="run-id">{currentRun.run_id}</span>
            <span className="separator">•</span>
            <span className="filename">{currentRun.filename}</span>
          </p>
        </div>
      </div>

      <div className="dashboard-body">
        {/* Summary Cards */}
        <SummaryCards
          totalRecords={currentRun.total_records}
          totalAnomalies={currentRun.total_anomalies}
          severitySummary={currentRun.severity_summary}
          overallDataQualityScore={statistics?.overall_data_quality_score}
        />

        {/* Filters and Controls */}
        <Filters onDownload={handleDownload} isDownloading={isDownloading} />

        {/* Anomalies Table */}
        {error && (
          <div className="error-banner">
            <span className="error-icon">⚠️</span>
            {error}
          </div>
        )}

        {isLoading ? (
          <div className="loading-container">
            <div className="spinner"></div>
            <p className="loading-text">Loading anomalies...</p>
          </div>
        ) : anomalies.length === 0 ? (
          <div className="empty-state">
            <p className="empty-icon">🔍</p>
            <h3>No anomalies found</h3>
            <p>Try adjusting your filters or search criteria</p>
          </div>
        ) : (
          <>
            <AnomaliesTable
              anomalies={anomalies}
              onSelectAnomaly={setSelectedAnomaly}
            />

            {/* Pagination */}
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
                <span className="text-muted"> • {totalAnomalies} total anomalies</span>
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
      </div>

      {/* Detail Modal */}
      {selectedAnomaly && (
        <AnomalyDetail
          anomaly={selectedAnomaly}
          onClose={() => setSelectedAnomaly(null)}
        />
      )}
    </div>
  )
}
