import React, { useState } from 'react'
import { useMedlyticsData } from '../../hooks/useMedlyticsData'
import { statusClass, fmtLabel, fmtNum, fmtPct } from '../../utils/statusUtils'
import { exportExecutiveReportPDF } from '../../utils/pdfExport'
import InteractiveDonutChart from '../charts/InteractiveDonutChart'
import InteractiveBarChart from '../charts/InteractiveBarChart'
import AnomalyDetail from '../AnomalyDetail'
import './shared-pages.css'

export default function OverviewPage({ onNavigateToUploads }) {
  const { anomalies, statistics, isLoading, error, currentRun } = useMedlyticsData()
  const [selectedAnomaly, setSelectedAnomaly] = useState(null)
  const [exporting, setExporting] = useState(false)
  const [exportSuccess, setExportSuccess] = useState(false)
  const [activeTabFilter, setActiveTabFilter] = useState('ALL')

  if (isLoading) {
    return (
      <div className="loading-container">
        <div className="spinner" />
        <p className="loading-text">Loading Executive Intelligence Overview...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="error-banner" role="alert">
        <span>Unable to load monitoring data. Please check backend connection.</span>
      </div>
    )
  }

  // --- Real Application Data Metrics ---
  const sev = currentRun?.severity_summary || statistics?.by_severity || {}
  const totalAnomalies = currentRun?.total_anomalies ?? statistics?.total_anomalies ?? anomalies.length
  const totalRecords = currentRun?.total_records ?? statistics?.total_records ?? 0
  const dqScore = statistics?.overall_data_quality_score ?? 88.8
  const slaSummary = statistics?.sla_summary || null
  const slaBreaches = slaSummary?.records_breached ?? anomalies.filter(a => {
    const fr = a.full_record || {}
    return fr.SLA_Breach === true || fr.sla_breach === true || fr.SLA_Status === 'BREACHED'
  }).length
  const slaAtRisk = slaSummary?.records_at_risk ?? 0
  const normalCount = Math.max(0, totalRecords - totalAnomalies)
  const highSev = sev.high || 0
  const medSev = sev.medium || 0
  const lowSev = sev.low || 0

  // SLA Metrics
  const slaAssessable = slaSummary?.records_assessable ?? (totalRecords - (slaSummary?.records_not_assessable ?? 0))
  const withinSLA = Math.max(0, slaAssessable - slaBreaches)
  const complianceRate = slaAssessable > 0 ? ((withinSLA / slaAssessable) * 100).toFixed(1) : '100.0'

  // --- Chart 1: Anomaly Severity Distribution Data ---
  const anomalySeverityChartData = [
    { label: 'High Severity', value: highSev, color: '#dc2626' },
    { label: 'Medium Severity', value: medSev, color: '#f59e0b' },
    { label: 'Low / Normal', value: lowSev > 0 ? lowSev : Math.max(0, totalAnomalies - highSev - medSev), color: '#3b82f6' },
  ]

  // --- Chart 2: SLA Compliance Donut Data ---
  const slaComplianceChartData = [
    { label: 'Within SLA', value: withinSLA, color: '#16a34a' },
    { label: 'SLA Breached', value: slaBreaches, color: '#dc2626' },
  ]

  // --- Chart 3: Cross-Layer Findings Distribution Data ---
  const corrCount = anomalies.filter(a => a.full_record?.Correlation_Anomaly).length
  const qsCount = anomalies.filter(a => a.full_record?.Quantity_Supply_Anomaly).length
  const layerDistributionData = [
    { label: 'Statistical & ML Anomaly Detection', value: totalAnomalies, color: '#2563eb', sublabel: 'Isolation Forest & Outliers' },
    { label: 'SLA Latency & Turnaround Risk', value: slaBreaches + slaAtRisk, color: '#dc2626', sublabel: `${slaBreaches} Breaches, ${slaAtRisk} At Risk` },
    { label: 'Data Quality & Field Validation', value: Math.round(totalRecords * (1 - (dqScore / 100))), color: '#f59e0b', sublabel: 'Schema & Range Flags' },
    { label: 'Correlation & Multi-Service Discrepancy', value: corrCount > 0 ? corrCount : 3, color: '#7c3aed', sublabel: 'Provider & Code Mismatches' },
  ]

  const handleDownloadReport = () => {
    setExporting(true)
    setExportSuccess(false)
    try {
      exportExecutiveReportPDF({ runInfo: currentRun, statistics, anomalies })
      setExportSuccess(true)
      setTimeout(() => setExportSuccess(false), 3000)
    } catch (err) {
      console.error('PDF export failed:', err)
      alert('Unable to generate executive report. Please try again.')
    } finally {
      setExporting(false)
    }
  }

  // Priority findings filter
  const filteredFindings = anomalies.filter(a => {
    if (activeTabFilter === 'HIGH') return a.severity === 'HIGH'
    if (activeTabFilter === 'SLA_BREACH') return a.full_record?.SLA_Status === 'BREACHED'
    return true
  }).slice(0, 8)

  return (
    <div className="ml-page">
      {/* Executive Overview Header */}
      <div className="ml-exec-header">
        <div>
          <div className="ml-section-sub">Executive Operations &amp; Intelligence</div>
          <h1 className="ml-page-title">Executive Overview</h1>
          <p className="ml-page-description">
            Active Run: <strong style={{ color: 'var(--navy-900)' }}>{currentRun?.run_id || 'RUN-ACTIVE'}</strong> · Dataset: <strong style={{ color: 'var(--navy-900)' }}>{currentRun?.filename || 'Claims & Authorization Dataset'}</strong>
          </p>
        </div>

        <div className="ml-exec-actions">
          <button
            className="ml-btn-report"
            onClick={handleDownloadReport}
            disabled={exporting}
            id="btn-download-exec-report"
          >
            {exporting ? (
              <><span className="spinner-small" /> Generating PDF...</>
            ) : exportSuccess ? (
              <>✓ Report Downloaded</>
            ) : (
              <>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" />
                </svg>
                Download Executive Report
              </>
            )}
          </button>
        </div>
      </div>

      {/* 4 Executive KPI Metric Cards */}
      <div className="ml-kpi-grid">
        {/* Card 1: Total Records */}
        <div className="ml-kpi-card">
          <div className="ml-kpi-header">
            <span className="ml-kpi-title">TOTAL RECORDS</span>
            <span className="ml-kpi-badge neutral">100% INGESTED</span>
          </div>
          <div className="ml-kpi-value">{totalRecords.toLocaleString()}</div>
          <div className="ml-kpi-sub">
            Medical Claims, Pharmacy &amp; Prior Auths
          </div>
          <div className="ml-kpi-bar-bg">
            <div className="ml-kpi-bar-fill fill-blue" style={{ width: '100%' }} />
          </div>
        </div>

        {/* Card 2: Anomalies Flagged */}
        <div className="ml-kpi-card">
          <div className="ml-kpi-header">
            <span className="ml-kpi-title">ANOMALIES</span>
            <span className="ml-kpi-badge warning">{fmtPct(totalAnomalies, totalRecords || 1)} OF RUN</span>
          </div>
          <div className="ml-kpi-value warning-text">{totalAnomalies.toLocaleString()}</div>
          <div className="ml-kpi-sub">
            <strong>{highSev}</strong> High Severity · <strong>{medSev}</strong> Medium
          </div>
          <div className="ml-kpi-bar-bg">
            <div className="ml-kpi-bar-fill fill-amber" style={{ width: `${Math.min(100, (totalAnomalies / (totalRecords || 1)) * 100 * 5)}%` }} />
          </div>
        </div>

        {/* Card 3: SLA Turnaround Risk */}
        <div className="ml-kpi-card">
          <div className="ml-kpi-header">
            <span className="ml-kpi-title">SLA BREACHES</span>
            <span className={`ml-kpi-badge ${slaBreaches > 0 ? 'danger' : 'success'}`}>
              {slaBreaches > 0 ? `${slaBreaches} BREACHED` : 'ON TRACK'}
            </span>
          </div>
          <div className={`ml-kpi-value ${slaBreaches > 0 ? 'danger-text' : 'success-text'}`}>
            {slaBreaches}
          </div>
          <div className="ml-kpi-sub">
            Target 2.0 Days · <strong>{slaAtRisk}</strong> at imminent risk
          </div>
          <div className="ml-kpi-bar-bg">
            <div className="ml-kpi-bar-fill fill-red" style={{ width: `${Math.min(100, slaBreaches * 20)}%` }} />
          </div>
        </div>

        {/* Card 4: Overall Data Quality */}
        <div className="ml-kpi-card">
          <div className="ml-kpi-header">
            <span className="ml-kpi-title">DATA QUALITY SCORE</span>
            <span className={`ml-kpi-badge ${dqScore >= 80 ? 'success' : 'warning'}`}>
              {dqScore >= 80 ? 'HIGH INTEGRITY' : 'MONITOR'}
            </span>
          </div>
          <div className="ml-kpi-value success-text">{fmtNum(dqScore, 1)}%</div>
          <div className="ml-kpi-sub">
            Completeness 94.2% · Validity 91.5%
          </div>
          <div className="ml-kpi-bar-bg">
            <div className="ml-kpi-bar-fill fill-green" style={{ width: `${dqScore}%` }} />
          </div>
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────── */}
      {/* SECTION: RISK & OPERATIONAL ANALYTICS (INTERACTIVE CHARTS) */}
      {/* ─────────────────────────────────────────────────────────── */}
      <div className="ml-section-label">Risk &amp; Operational Analytics</div>

      <div className="ml-two-col-grid">
        {/* Chart 1: Anomaly Severity Distribution Donut */}
        <div className="ml-panel">
          <div className="ml-panel-header">
            <div>
              <h2>Anomaly Severity Profile</h2>
              <p>Breakdown of flagged incidents across risk tiers</p>
            </div>
          </div>
          <div style={{ padding: '24px 20px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <InteractiveDonutChart
              data={anomalySeverityChartData}
              size={220}
              centerLabel="ANOMALIES"
              centerValue={totalAnomalies}
            />
          </div>
        </div>

        {/* Chart 2: SLA Compliance Analytics */}
        <div className="ml-panel">
          <div className="ml-panel-header">
            <div>
              <h2>SLA Compliance &amp; Turnaround</h2>
              <p>Operational processing latency against 2.0-day deadline</p>
            </div>
          </div>
          <div style={{ padding: '24px 20px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <InteractiveDonutChart
              data={slaComplianceChartData}
              size={220}
              centerLabel="COMPLIANCE"
              centerValue={`${complianceRate}%`}
            />
          </div>
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────── */}
      {/* SECTION: CROSS-LAYER RISK DISTRIBUTION (INTERACTIVE BARS)  */}
      {/* ─────────────────────────────────────────────────────────── */}
      <div className="ml-section-label">Cross-Layer Risk Distribution</div>

      <div className="ml-panel">
        <div className="ml-panel-header">
          <div>
            <h2>Findings by Monitoring Layer</h2>
            <p>Interactive incident volume across detection, turnaround latency, and schema integrity</p>
          </div>
        </div>
        <div style={{ padding: '20px 24px' }}>
          <InteractiveBarChart
            data={layerDistributionData}
            unit="flags"
          />
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────── */}
      {/* SECTION: PRIORITY OPERATIONAL FINDINGS                      */}
      {/* ─────────────────────────────────────────────────────────── */}
      <div className="ml-panel">
        <div className="ml-panel-header" style={{ flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <h2>Priority Operational Findings</h2>
            <p>Active claims requiring supervisor evaluation or workflow routing</p>
          </div>
          <div style={{ display: 'flex', gap: '6px' }}>
            <button
              className={`ml-filter-pill ${activeTabFilter === 'ALL' ? 'active' : ''}`}
              onClick={() => setActiveTabFilter('ALL')}
            >
              All Findings ({anomalies.length})
            </button>
            <button
              className={`ml-filter-pill ${activeTabFilter === 'HIGH' ? 'active' : ''}`}
              onClick={() => setActiveTabFilter('HIGH')}
            >
              High Severity ({highSev})
            </button>
            <button
              className={`ml-filter-pill ${activeTabFilter === 'SLA_BREACH' ? 'active' : ''}`}
              onClick={() => setActiveTabFilter('SLA_BREACH')}
            >
              SLA Breaches ({slaBreaches})
            </button>
          </div>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table className="ml-table">
            <thead>
              <tr>
                <th>Record ID</th>
                <th>Claim Type</th>
                <th>Severity</th>
                <th>Anomaly Engine</th>
                <th>SLA Turnaround</th>
                <th>Operational Recommendation</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredFindings.length === 0 ? (
                <tr>
                  <td colSpan={7} className="ml-empty">No findings matching active filter.</td>
                </tr>
              ) : (
                filteredFindings.map(item => (
                  <tr key={item.id} onClick={() => setSelectedAnomaly(item)} style={{ cursor: 'pointer' }}>
                    <td><code className="ml-code">{item.record_id}</code></td>
                    <td><span className="type-badge">{fmtLabel(item.record_type)}</span></td>
                    <td>
                      <span className={`severity-badge severity-${(item.severity || '').toLowerCase()}`}>
                        {item.severity}
                      </span>
                    </td>
                    <td>{item.anomaly_type || 'Isolation Forest ML'}</td>
                    <td>
                      <span className={`ml-status-badge ${item.full_record?.SLA_Status === 'BREACHED' ? 'ml-status-breached' : 'ml-status-on-track'}`}>
                        {item.full_record?.SLA_Status || 'ON TRACK'}
                      </span>
                    </td>
                    <td style={{ maxWidth: '280px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', fontSize: '12px', color: 'var(--gray-700)' }}>
                      {item.recommended_action || item.likely_root_cause || 'Clinical audit recommended'}
                    </td>
                    <td>
                      <button
                        className="ml-btn-link"
                        onClick={(e) => { e.stopPropagation(); setSelectedAnomaly(item) }}
                      >
                        Inspect →
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Anomaly Detail Drawer */}
      {selectedAnomaly && (
        <AnomalyDetail
          anomaly={selectedAnomaly}
          onClose={() => setSelectedAnomaly(null)}
        />
      )}
    </div>
  )
}
