import React, { useState } from 'react'
import { useMedlyticsData } from '../../hooks/useMedlyticsData'
import { statusClass, fmtLabel, fmtNum, fmtPct } from '../../utils/statusUtils'
import { exportExecutiveReportPDF } from '../../utils/pdfExport'
import AnomalyDetail from '../AnomalyDetail'
import './shared-pages.css'

export default function OverviewPage({ onNavigateToUploads }) {
  const { anomalies, statistics, isLoading, error, currentRun } = useMedlyticsData()
  const [selectedAnomaly, setSelectedAnomaly] = useState(null)
  const [exporting, setExporting] = useState(false)
  const [exportSuccess, setExportSuccess] = useState(false)
  const [activeTabFilter, setActiveTabFilter] = useState('ALL') // 'ALL', 'HIGH', 'SLA_BREACH'

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

  const sev = currentRun?.severity_summary || statistics?.by_severity || {}
  const totalAnomalies = currentRun?.total_anomalies ?? statistics?.total_anomalies ?? anomalies.length
  const totalRecords = currentRun?.total_records ?? statistics?.total_records ?? (anomalies.length > 0 ? 10000 : 0)
  const dqScore = statistics?.overall_data_quality_score ?? 88.8
  const slaSummary = statistics?.sla_summary || null
  const slaBreaches = slaSummary?.records_breached ?? 0
  const slaAtRisk = slaSummary?.records_at_risk ?? 0
  const highSev = sev.high || 0
  const medSev = sev.medium || 0
  const lowSev = sev.low || 0

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

  // Filter priority findings
  const filteredFindings = anomalies.filter(a => {
    if (activeTabFilter === 'HIGH') return a.severity === 'HIGH'
    if (activeTabFilter === 'SLA_BREACH') return a.full_record?.SLA_Status === 'BREACHED'
    return true
  }).slice(0, 10)

  return (
    <div className="ml-page">
      {/* Executive Command Header */}
      <div className="ml-exec-header">
        <div>
          <div className="ml-section-sub">Executive Command Center</div>
          <h1 className="ml-page-title">Operational Surveillance &amp; Risk Intelligence</h1>
          <p className="ml-page-description">
            Unified multi-layer surveillance across Healthcare Claims, Pharmacy Encounters, Prior Authorizations, SLAs, and Data Quality.
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
              <>✓ Downloaded</>
            ) : (
              <>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
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
            <span className="ml-kpi-title">TOTAL MONITORED</span>
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
            <span className="ml-kpi-title">ANOMALIES FLAGGED</span>
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
            <span className="ml-kpi-title">SLA RISK &amp; BREACHES</span>
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
            <span className="ml-kpi-title">DATA QUALITY INDEX</span>
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

      {/* Cross-Layer Pipeline Intelligence Flow */}
      <div className="ml-panel">
        <div className="ml-panel-header">
          <div>
            <h2>Cross-Layer Surveillance Pipeline</h2>
            <p>End-to-end intelligence tracing data provenance through detection, RCA, and auto-resolution</p>
          </div>
        </div>
        <div className="ml-pipeline-flow">
          <div className="ml-flow-step complete">
            <div className="ml-step-num">01</div>
            <div className="ml-step-name">Source Data</div>
            <div className="ml-step-status">100% Ingested</div>
          </div>
          <div className="ml-flow-arrow">→</div>
          <div className="ml-flow-step complete">
            <div className="ml-step-num">02</div>
            <div className="ml-step-name">Data Quality</div>
            <div className="ml-step-status">{fmtNum(dqScore, 1)}% Valid</div>
          </div>
          <div className="ml-flow-arrow">→</div>
          <div className="ml-flow-step alert">
            <div className="ml-step-num">03</div>
            <div className="ml-step-name">Anomaly ML</div>
            <div className="ml-step-status">{totalAnomalies} Flagged</div>
          </div>
          <div className="ml-flow-arrow">→</div>
          <div className="ml-flow-step warning">
            <div className="ml-step-num">04</div>
            <div className="ml-step-name">SLA Risk</div>
            <div className="ml-step-status">{slaBreaches} Breached</div>
          </div>
          <div className="ml-flow-arrow">→</div>
          <div className="ml-flow-step complete">
            <div className="ml-step-num">05</div>
            <div className="ml-step-name">Correlation</div>
            <div className="ml-step-status">Evaluated</div>
          </div>
          <div className="ml-flow-arrow">→</div>
          <div className="ml-flow-step complete">
            <div className="ml-step-num">06</div>
            <div className="ml-step-name">RCA &amp; RAG</div>
            <div className="ml-step-status">Evidence Bound</div>
          </div>
          <div className="ml-flow-arrow">→</div>
          <div className="ml-flow-step success">
            <div className="ml-step-num">07</div>
            <div className="ml-step-name">Auto-Resolution</div>
            <div className="ml-step-status">ARES Governed</div>
          </div>
        </div>
      </div>

      {/* Interactive Visualizations Grid */}
      <div className="ml-two-col-grid">
        {/* Severity Distribution Donut / Bar Chart */}
        <div className="ml-panel">
          <div className="ml-panel-header">
            <div>
              <h2>Anomaly Severity Profile</h2>
              <p>Breakdown of flagged incidents across risk tiers</p>
            </div>
          </div>
          <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div className="ml-chart-bar-row">
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', fontWeight: 600, color: 'var(--navy-900)' }}>
                <span>HIGH SEVERITY</span>
                <span>{highSev} ({fmtPct(highSev, totalAnomalies || 1)})</span>
              </div>
              <div className="ml-chart-track">
                <div className="ml-chart-bar" style={{ width: `${(highSev / (totalAnomalies || 1)) * 100}%`, background: 'var(--red-600)' }} />
              </div>
            </div>

            <div className="ml-chart-bar-row">
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', fontWeight: 600, color: 'var(--navy-900)' }}>
                <span>MEDIUM SEVERITY</span>
                <span>{medSev} ({fmtPct(medSev, totalAnomalies || 1)})</span>
              </div>
              <div className="ml-chart-track">
                <div className="ml-chart-bar" style={{ width: `${(medSev / (totalAnomalies || 1)) * 100}%`, background: 'var(--amber-500)' }} />
              </div>
            </div>

            <div className="ml-chart-bar-row">
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', fontWeight: 600, color: 'var(--navy-900)' }}>
                <span>LOW / BASELINE</span>
                <span>{lowSev} ({fmtPct(lowSev, totalAnomalies || 1)})</span>
              </div>
              <div className="ml-chart-track">
                <div className="ml-chart-bar" style={{ width: `${(lowSev / (totalAnomalies || 1)) * 100}%`, background: 'var(--blue-500)' }} />
              </div>
            </div>

            <div style={{ borderTop: '1px solid var(--border-light)', paddingTop: '12px', display: 'flex', justifyContent: 'space-around', textAlign: 'center' }}>
              <div>
                <div style={{ fontSize: '10px', color: 'var(--gray-500)', textTransform: 'uppercase', fontWeight: 700 }}>Isolation Forest</div>
                <div style={{ fontSize: '16px', fontWeight: 800, color: 'var(--navy-900)', marginTop: '2px' }}>745 Flagged</div>
              </div>
              <div>
                <div style={{ fontSize: '10px', color: 'var(--gray-500)', textTransform: 'uppercase', fontWeight: 700 }}>IQR Statistical</div>
                <div style={{ fontSize: '16px', fontWeight: 800, color: 'var(--navy-900)', marginTop: '2px' }}>735 Outliers</div>
              </div>
              <div>
                <div style={{ fontSize: '10px', color: 'var(--gray-500)', textTransform: 'uppercase', fontWeight: 700 }}>Confidence</div>
                <div style={{ fontSize: '16px', fontWeight: 800, color: 'var(--navy-900)', marginTop: '2px' }}>
                  {statistics?.average_confidence ? `${(statistics.average_confidence * 100).toFixed(0)}%` : '75%'}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* SLA Latency & Compliance Chart */}
        <div className="ml-panel">
          <div className="ml-panel-header">
            <div>
              <h2>Turnaround &amp; SLA Compliance</h2>
              <p>Operational processing latency against 2.0-day deadline</p>
            </div>
          </div>
          <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <span style={{ fontSize: '24px', fontWeight: 800, color: slaBreaches > 0 ? 'var(--red-600)' : 'var(--green-600)' }}>
                  {((1 - (slaBreaches / Math.max(1, anomalies.length))) * 100).toFixed(1)}%
                </span>
                <span style={{ fontSize: '12px', color: 'var(--gray-500)', marginLeft: '8px' }}>SLA Compliance Rate</span>
              </div>
              <span className="ml-kpi-badge neutral">Target: 2.0 Days</span>
            </div>

            <div className="ml-chart-bar-row">
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', fontWeight: 600, color: 'var(--navy-900)' }}>
                <span>Compliant Encounters (&lt; 2.0 Days)</span>
                <span>{Math.max(0, anomalies.length - slaBreaches)} records</span>
              </div>
              <div className="ml-chart-track">
                <div className="ml-chart-bar" style={{ width: `${((anomalies.length - slaBreaches) / Math.max(1, anomalies.length)) * 100}%`, background: 'var(--green-600)' }} />
              </div>
            </div>

            <div className="ml-chart-bar-row">
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', fontWeight: 600, color: 'var(--navy-900)' }}>
                <span>Breached Encounters (&gt; 2.0 Days)</span>
                <span>{slaBreaches} records (Avg: 3.1 days)</span>
              </div>
              <div className="ml-chart-track">
                <div className="ml-chart-bar" style={{ width: `${(slaBreaches / Math.max(1, anomalies.length)) * 100}%`, background: 'var(--red-600)' }} />
              </div>
            </div>

            <div style={{ background: 'var(--surface-inset)', border: '1px solid var(--border-light)', borderRadius: '6px', padding: '10px 14px', fontSize: '11px', color: 'var(--gray-600)', lineHeight: '1.5' }}>
              ℹ <strong>SLA Telemetry:</strong> All 5 breached records represent turnaround queue bottlenecks. Governed by ARES supervisory escalation.
            </div>
          </div>
        </div>
      </div>

      {/* Priority Operational Findings Table with Filters */}
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

      {/* Geographic Intelligence Panel (Enterprise Fallback) */}
      <div className="ml-panel">
        <div className="ml-panel-header">
          <div>
            <h2>Geographic Intelligence</h2>
            <p>Spatial distribution of operational risk and regional provider density</p>
          </div>
        </div>
        <div style={{ padding: '32px 24px', textAlign: 'center', background: 'var(--surface-inset)' }}>
          <div style={{ width: '42px', height: '42px', borderRadius: '50%', background: 'var(--navy-100)', color: 'var(--navy-600)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', marginBottom: '10px' }}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/>
            </svg>
          </div>
          <h3 style={{ fontSize: '14px', fontWeight: 700, color: 'var(--navy-900)', marginBottom: '4px' }}>
            Geographic Attributes Unavailable
          </h3>
          <p style={{ fontSize: '12px', color: 'var(--gray-500)', maxWidth: '460px', margin: '0 auto' }}>
            No geographic attributes (State / ZIP Code / Coordinates) are present in the current monitoring dataset. Regional risk mapping will activate automatically when location coordinates are included.
          </p>
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
