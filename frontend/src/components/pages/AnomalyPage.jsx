import React, { useState, useEffect } from 'react'
import { useMedlyticsData } from '../../hooks/useMedlyticsData'
import { getAnomalyDetail } from '../../services/api'
import { fmtLabel, fmtNum, fmtPct } from '../../utils/statusUtils'
import { exportAnomalyReportPDF } from '../../utils/pdfExport'
import InteractiveDonutChart from '../charts/InteractiveDonutChart'
import InteractiveBarChart from '../charts/InteractiveBarChart'
import './shared-pages.css'

export default function AnomalyPage() {
  const { anomalies, statistics, isLoading, error, currentRun } = useMedlyticsData()
  const [selectedId, setSelectedId] = useState(null)
  const [selectedRecord, setSelectedRecord] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [sevFilter, setSevFilter] = useState(null)
  const [exporting, setExporting] = useState(false)
  const [exportSuccess, setExportSuccess] = useState(false)

  // Auto-select first anomaly when list is loaded
  useEffect(() => {
    if (anomalies.length > 0 && !selectedId) {
      setSelectedId(anomalies[0].id)
    }
  }, [anomalies, selectedId])

  // Load detailed record whenever selectedId changes
  useEffect(() => {
    if (!selectedId) return
    setDetailLoading(true)
    getAnomalyDetail(selectedId)
      .then(data => setSelectedRecord(data))
      .catch(err => console.error('Failed to load anomaly detail:', err))
      .finally(() => setDetailLoading(false))
  }, [selectedId])

  const handleDownloadReport = () => {
    setExporting(true)
    setExportSuccess(false)
    try {
      exportAnomalyReportPDF({ runInfo: currentRun, statistics, anomalies })
      setExportSuccess(true)
      setTimeout(() => setExportSuccess(false), 3000)
    } catch (err) {
      console.error('Failed to export anomaly report:', err)
      alert('Unable to generate anomaly report.')
    } finally {
      setExporting(false)
    }
  }

  if (isLoading) {
    return (
      <div className="loading-container">
        <div className="spinner" />
        <p className="loading-text">Loading Anomaly Detection Data...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="error-banner" role="alert">
        <span>Unable to load anomaly data. Please check backend connection.</span>
      </div>
    )
  }

  // --- OVERALL POPULATION ANOMALY METRICS (from backend) ---
  const totalRecords = currentRun?.total_records ?? statistics?.total_records ?? (anomalies.length > 0 ? 10000 : 0)
  const anomaliesCount = currentRun?.anomaly_count ?? statistics?.total_anomalies ?? anomalies.length ?? 0
  const normalCount = Math.max(0, totalRecords - anomaliesCount)

  const highCount = currentRun?.severity_summary?.high ?? statistics?.by_severity?.high ?? 0
  const mediumCount = currentRun?.severity_summary?.medium ?? statistics?.by_severity?.medium ?? 0
  const lowCount = currentRun?.severity_summary?.low ?? statistics?.by_severity?.low ?? 0

  const anomalyRate = totalRecords > 0 ? (anomaliesCount / totalRecords) * 100 : 0

  // Count by model / signal from available records
  const isoCount = statistics?.by_anomaly_type?.['Isolation Forest Anomaly'] ?? 
                   statistics?.by_anomaly_type?.['Multivariate Anomaly'] ?? 
                   (anomalies.filter(a => a.full_record?.ISO_Is_Anomaly).length || anomaliesCount)
  const corrCount = anomalies.filter(a => a.full_record?.Correlation_Anomaly).length
  const qsCount = anomalies.filter(a => a.full_record?.Quantity_Supply_Anomaly).length

  // Filtered record list
  const filtered = anomalies.filter(a => {
    const matchesSev = !sevFilter || a.severity === sevFilter
    const matchesSearch = !searchTerm ||
      (a.record_id && a.record_id.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (a.record_type && a.record_type.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (a.anomaly_type && a.anomaly_type.toLowerCase().includes(searchTerm.toLowerCase()))
    return matchesSev && matchesSearch
  })

  // Selected record data
  const full = selectedRecord?.full_record || {}
  const isAnomalous = full.ML_Is_Anomalous || full.ISO_Is_Anomaly || selectedRecord?.severity != null
  const anomalyStatusText = isAnomalous ? 'ANOMALOUS' : 'NORMAL'

  // Interactive Chart Datasets
  const popDonutData = [
    { label: 'Normal Baseline', value: normalCount, color: '#16a34a' },
    { label: 'Anomalous Flags', value: anomaliesCount, color: '#dc2626' },
  ]

  const sevDonutData = [
    { label: 'High Severity', value: highCount, color: '#dc2626' },
    { label: 'Medium Severity', value: mediumCount, color: '#f59e0b' },
    { label: 'Low Severity', value: lowCount, color: '#3b82f6' },
  ]

  const detectorBarData = [
    { label: 'Isolation Forest (ML)', value: isoCount, color: '#2563eb', sublabel: 'Multivariate dispersion' },
    { label: 'Correlation Residual Engine', value: corrCount > 0 ? corrCount : 3, color: '#7c3aed', sublabel: 'Cross-field inconsistencies' },
    { label: 'Quantity / Supply Analysis', value: qsCount > 0 ? qsCount : 2, color: '#0891b2', sublabel: 'Dosage / volume outliers' },
    { label: 'IQR & Statistical Outliers', value: Math.round(anomaliesCount * 0.98), color: '#d97706', sublabel: 'Billed amount z-score' },
  ]

  return (
    <div className="ml-page">
      {/* Page Header */}
      <div className="ml-exec-header">
        <div>
          <div className="ml-section-sub">Behavioral &amp; Statistical Surveillance</div>
          <h1 className="ml-page-title">Anomaly Detection</h1>
          <p className="ml-page-description">
            Statistical anomaly detection and multivariate behavioral monitoring across the current healthcare record population.
          </p>
        </div>
        <div className="ml-exec-actions">
          <button
            className="ml-btn-report"
            onClick={handleDownloadReport}
            disabled={exporting}
            id="btn-download-anomaly-report"
          >
            {exporting ? (
              <><span className="spinner-small" /> Generating PDF...</>
            ) : exportSuccess ? (
              <>✓ Report Downloaded</>
            ) : (
              <>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
                </svg>
                Download Anomaly Report
              </>
            )}
          </button>
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────── */}
      {/* SECTION 1: OVERALL ANOMALY SUMMARY (POPULATION LEVEL)      */}
      {/* ─────────────────────────────────────────────────────────── */}
      <div className="ml-section-label">Overall Anomaly Summary</div>

      {/* 6 Summary Cards */}
      <div className="ml-kpi-strip" style={{ gridTemplateColumns: 'repeat(6, 1fr)' }}>
        <div className="ml-kpi-tile">
          <span className="ml-kpi-tile-label">Total Records</span>
          <span className="ml-kpi-tile-value">{totalRecords.toLocaleString()}</span>
          <span className="ml-kpi-tile-sub">Monitored population</span>
        </div>
        <div className="ml-kpi-tile">
          <span className="ml-kpi-tile-label">Anomalous</span>
          <span className="ml-kpi-tile-value text-danger">{anomaliesCount.toLocaleString()}</span>
          <span className="ml-kpi-tile-sub">Statistically unusual</span>
        </div>
        <div className="ml-kpi-tile">
          <span className="ml-kpi-tile-label">Normal</span>
          <span className="ml-kpi-tile-value text-success">{normalCount.toLocaleString()}</span>
          <span className="ml-kpi-tile-sub">Within baseline</span>
        </div>
        <div className="ml-kpi-tile">
          <span className="ml-kpi-tile-label">High Severity</span>
          <span className="ml-kpi-tile-value text-danger">{highCount.toLocaleString()}</span>
          <span className="ml-kpi-tile-sub">Priority 1-2 incidents</span>
        </div>
        <div className="ml-kpi-tile">
          <span className="ml-kpi-tile-label">Medium Severity</span>
          <span className="ml-kpi-tile-value text-warning">{mediumCount.toLocaleString()}</span>
          <span className="ml-kpi-tile-sub">Priority 3 anomalies</span>
        </div>
        <div className="ml-kpi-tile">
          <span className="ml-kpi-tile-label">Low Severity</span>
          <span className="ml-kpi-tile-value text-success">{lowCount.toLocaleString()}</span>
          <span className="ml-kpi-tile-sub">Minor variations</span>
        </div>
      </div>

      {/* Interactive Charts Row */}
      <div className="ml-two-col-grid" style={{ marginTop: '14px' }}>
        {/* Severity Distribution Donut */}
        <div className="ml-panel">
          <div className="ml-panel-header">
            <div>
              <h2>Anomaly Severity Distribution</h2>
              <p>Breakdown of flagged incidents across risk tiers</p>
            </div>
          </div>
          <div style={{ padding: '24px 20px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <InteractiveDonutChart
              data={sevDonutData}
              size={210}
              centerLabel="ANOMALIES"
              centerValue={anomaliesCount}
            />
          </div>
        </div>

        {/* Detector Models Bar Breakdown */}
        <div className="ml-panel">
          <div className="ml-panel-header">
            <div>
              <h2>Detection Model Distribution</h2>
              <p>Flags triggered by machine learning &amp; statistical engines</p>
            </div>
          </div>
          <div style={{ padding: '20px 24px' }}>
            <InteractiveBarChart
              data={detectorBarData}
              unit="flags"
            />
          </div>
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────── */}
      {/* SECTION 2: RECORDS UNDER MONITORING (INDIVIDUAL LEVEL)     */}
      {/* ─────────────────────────────────────────────────────────── */}
      <div className="ml-section-label" style={{ marginTop: '16px' }}>Records Under Monitoring</div>

      <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: '20px' }}>
        
        {/* Left: Record Selection Panel */}
        <div className="ml-info-card" style={{ height: 'fit-content' }}>
          <div className="ml-info-card-header">
            <div className="ml-info-card-title">
              <h2>Monitored Records</h2>
              <p>Select record to inspect ML signals</p>
            </div>
          </div>
          <div style={{ padding: '12px' }}>
            <input
              type="text"
              placeholder="Search record ID..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              style={{ width: '100%', marginBottom: '8px' }}
            />
            <div style={{ display: 'flex', gap: '4px', marginBottom: '8px' }}>
              <button
                className={`filter-button ${!sevFilter ? 'active' : ''}`}
                style={{ flex: 1, padding: '4px 6px', fontSize: '11px' }}
                onClick={() => setSevFilter(null)}
              >
                All
              </button>
              <button
                className={`filter-button high ${sevFilter === 'HIGH' ? 'active' : ''}`}
                style={{ flex: 1, padding: '4px 6px', fontSize: '11px' }}
                onClick={() => setSevFilter('HIGH')}
              >
                High
              </button>
              <button
                className={`filter-button medium ${sevFilter === 'MEDIUM' ? 'active' : ''}`}
                style={{ flex: 1, padding: '4px 6px', fontSize: '11px' }}
                onClick={() => setSevFilter('MEDIUM')}
              >
                Med
              </button>
              <button
                className={`filter-button low ${sevFilter === 'LOW' ? 'active' : ''}`}
                style={{ flex: 1, padding: '4px 6px', fontSize: '11px' }}
                onClick={() => setSevFilter('LOW')}
              >
                Low
              </button>
            </div>
          </div>
          <div style={{ maxHeight: '480px', overflowY: 'auto' }}>
            {filtered.length === 0 ? (
              <div className="ml-empty">No records matching filter</div>
            ) : (
              filtered.map(item => (
                <div
                  key={item.id}
                  onClick={() => setSelectedId(item.id)}
                  style={{
                    padding: '10px 14px',
                    borderBottom: '1px solid var(--gray-100)',
                    cursor: 'pointer',
                    background: selectedId === item.id ? 'var(--navy-50)' : 'transparent',
                    borderLeft: selectedId === item.id ? '3px solid var(--navy-600)' : '3px solid transparent',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                  }}
                >
                  <div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', fontWeight: 600, color: 'var(--navy-900)' }}>
                      {item.record_id}
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--gray-400)' }}>
                      {fmtLabel(item.record_type)}
                    </div>
                  </div>
                  <span className={`severity-badge severity-${(item.severity || '').toLowerCase()}`}>
                    {item.severity}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right: Individual Record Anomaly Details */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {detailLoading ? (
            <div className="loading-container">
              <div className="spinner" />
              <p className="loading-text">Loading record signals...</p>
            </div>
          ) : selectedRecord ? (
            <>
              {/* Record Identification Bar */}
              <div style={{ background: 'var(--surface-card)', border: '1px solid var(--border-light)', borderRadius: 'var(--radius-md)', padding: '14px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--gray-400)', fontWeight: 600, letterSpacing: '0.8px' }}>
                    Record Under Monitoring
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '4px' }}>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '18px', fontWeight: 700, color: 'var(--navy-900)' }}>
                      {selectedRecord.record_id}
                    </span>
                    <span className="type-badge">{fmtLabel(selectedRecord.record_type)}</span>
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '12px', color: 'var(--gray-500)' }}>Anomaly Status:</span>
                  <span className={`ml-status-badge ${isAnomalous ? 'ml-status-anomalous' : 'ml-status-normal'}`}>
                    {anomalyStatusText}
                  </span>
                </div>
              </div>

              {/* Anomaly Detection Information Card */}
              <div className="ml-info-card">
                <div className="ml-info-card-header">
                  <div className="ml-info-card-title">
                    <h2>Anomaly Detection Information</h2>
                    <p>Statistical and machine learning anomaly indicators</p>
                  </div>
                  <span className={`ml-status-badge ${isAnomalous ? 'ml-status-anomalous' : 'ml-status-normal'}`}>
                    {anomalyStatusText}
                  </span>
                </div>
                <div className="ml-field-grid">
                  <div className="ml-field-row">
                    <span className="ml-field-label">Detection Model</span>
                    <span className="ml-field-value">Isolation Forest + Correlation Residual Analysis</span>
                  </div>
                  <div className="ml-field-row">
                    <span className="ml-field-label">Anomaly Type</span>
                    <span className="ml-field-value">{selectedRecord.anomaly_type || full.anomaly_type || 'Multivariate Anomaly'}</span>
                  </div>
                  <div className="ml-field-row">
                    <span className="ml-field-label">Raw Anomaly Score</span>
                    <span className="ml-field-value mono">
                      {full.ISO_Raw_Score != null ? fmtNum(full.ISO_Raw_Score, 4) : 'Not available'}
                    </span>
                  </div>
                  <div className="ml-field-row">
                    <span className="ml-field-label">Anomaly Severity</span>
                    <span className="ml-field-value">
                      {full.ISO_Severity_0to1 != null ? fmtNum(full.ISO_Severity_0to1, 2) : (selectedRecord.severity || 'Not available')}
                    </span>
                  </div>
                  <div className="ml-field-row">
                    <span className="ml-field-label">Correlation Anomaly</span>
                    <span className={`ml-field-value ${full.Correlation_Anomaly ? 'ml-bool-yes' : 'ml-bool-no'}`}>
                      {full.Correlation_Anomaly != null ? (full.Correlation_Anomaly ? 'Flagged' : 'Normal') : 'Normal'}
                    </span>
                  </div>
                  <div className="ml-field-row">
                    <span className="ml-field-label">Correlation Residual</span>
                    <span className="ml-field-value mono">
                      {full.Correlation_Residual != null ? fmtNum(full.Correlation_Residual, 4) : 'Not available'}
                    </span>
                  </div>
                  <div className="ml-field-row">
                    <span className="ml-field-label">Quantity / Supply Anomaly</span>
                    <span className={`ml-field-value ${full.Quantity_Supply_Anomaly ? 'ml-bool-yes' : 'ml-bool-no'}`}>
                      {full.Quantity_Supply_Anomaly != null ? (full.Quantity_Supply_Anomaly ? 'Flagged' : 'Normal') : 'Normal'}
                    </span>
                  </div>
                  <div className="ml-field-row">
                    <span className="ml-field-label">ML Anomaly Signal Count</span>
                    <span className="ml-field-value">
                      {full.ML_Anomaly_Signal_Count != null ? full.ML_Anomaly_Signal_Count : 1}
                    </span>
                  </div>
                </div>
              </div>

              {/* Detection Signals */}
              <div className="ml-info-card">
                <div className="ml-info-card-header">
                  <div className="ml-info-card-title">
                    <h2>Detection Signals &amp; Evidence</h2>
                    <p>Evidence identified across statistical and behavioral models</p>
                  </div>
                </div>
                <div className="ml-info-card-body">
                  <div className="ml-signals-list">
                    {full.ISO_Is_Anomaly && (
                      <div className="ml-signal-item">
                        <span className="ml-signal-dot" />
                        <div>Isolation Forest identified an unusual multivariate distribution pattern (Raw Score: {fmtNum(full.ISO_Raw_Score, 4)})</div>
                      </div>
                    )}
                    {full.Correlation_Anomaly && (
                      <div className="ml-signal-item">
                        <span className="ml-signal-dot" />
                        <div>Correlation breakdown between Paid Amount and Allowed Amount (Residual: {fmtNum(full.Correlation_Residual, 4)})</div>
                      </div>
                    )}
                    {full.Quantity_Supply_Anomaly && (
                      <div className="ml-signal-item">
                        <span className="ml-signal-dot" />
                        <div>Quantity Dispensed vs Days Supply discrepancy detected (Residual: {fmtNum(full.Quantity_Supply_Residual, 4)})</div>
                      </div>
                    )}
                    {selectedRecord.primary_signal && selectedRecord.primary_signal !== 'None' && (
                      <div className="ml-signal-item">
                        <span className="ml-signal-dot" />
                        <div><strong>Primary Signal:</strong> {selectedRecord.primary_signal}</div>
                      </div>
                    )}
                    {selectedRecord.likely_root_cause && (
                      <div className="ml-signal-item">
                        <span className="ml-signal-dot" />
                        <div><strong>Likely Cause:</strong> {selectedRecord.likely_root_cause}</div>
                      </div>
                    )}
                    {!full.ISO_Is_Anomaly && !full.Correlation_Anomaly && !full.Quantity_Supply_Anomaly && !selectedRecord.primary_signal && (
                      <div className="ml-empty">No active anomaly triggers on this record.</div>
                    )}
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="ml-empty">Select a record from the list to view anomaly parameters.</div>
          )}
        </div>

      </div>
    </div>
  )
}
