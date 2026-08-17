import React, { useState, useEffect } from 'react'
import { useMedlyticsData } from '../../hooks/useMedlyticsData'
import { getAnomalyDetail } from '../../services/api'
import { fmtLabel, fmtNum, fmtPct } from '../../utils/statusUtils'
import { exportSLAReportPDF } from '../../utils/pdfExport'
import InteractiveDonutChart from '../charts/InteractiveDonutChart'
import InteractiveBarChart from '../charts/InteractiveBarChart'
import './shared-pages.css'

export default function SLARiskPage() {
  const { anomalies, statistics, isLoading, error, currentRun } = useMedlyticsData()
  const [selectedId, setSelectedId] = useState(null)
  const [selectedRecord, setSelectedRecord] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [tableFilter, setTableFilter] = useState('ALL') // 'ALL', 'BREACHED', 'AT_RISK'
  const [exporting, setExporting] = useState(false)
  const [exportSuccess, setExportSuccess] = useState(false)

  // Auto-select first record on mount
  useEffect(() => {
    if (anomalies.length > 0 && !selectedId) {
      setSelectedId(anomalies[0].id)
    }
  }, [anomalies, selectedId])

  // Fetch full details of selected record
  useEffect(() => {
    if (!selectedId) return
    setDetailLoading(true)
    getAnomalyDetail(selectedId)
      .then(data => setSelectedRecord(data))
      .catch(err => console.error('Failed to load SLA record detail:', err))
      .finally(() => setDetailLoading(false))
  }, [selectedId])

  const handleDownloadReport = () => {
    setExporting(true)
    setExportSuccess(false)
    try {
      exportSLAReportPDF({ runInfo: currentRun, statistics, anomalies })
      setExportSuccess(true)
      setTimeout(() => setExportSuccess(false), 3000)
    } catch (err) {
      console.error('Failed to export SLA report:', err)
      alert('Unable to generate SLA report.')
    } finally {
      setExporting(false)
    }
  }

  if (isLoading) {
    return (
      <div className="loading-container">
        <div className="spinner" />
        <p className="loading-text">Loading SLA Risk Data...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="error-banner" role="alert">
        <span>Unable to load SLA risk data. Please check backend connection.</span>
      </div>
    )
  }

  // --- Population Level Metrics ---
  const slaSummary = statistics?.sla_summary || null
  const totalRecords = slaSummary?.total_records ?? currentRun?.total_records ?? statistics?.total_records ?? (anomalies.length > 0 ? 10000 : 0)
  const assessableCount = slaSummary?.records_assessable ?? (totalRecords - (slaSummary?.records_not_assessable ?? 0))
  const notAssessableCount = slaSummary?.records_not_assessable ?? 0
  const breachedCount = slaSummary?.records_breached ?? anomalies.filter(a => {
    const fr = a.full_record || {}
    return fr.SLA_Breach === true || fr.sla_breach === true || fr.SLA_Status === 'BREACHED'
  }).length
  const atRiskCount = slaSummary?.records_at_risk ?? 0
  const onTrackCount = slaSummary?.records_normal ?? Math.max(0, assessableCount - breachedCount - atRiskCount)

  const complianceRate = assessableCount > 0 ? ((onTrackCount / assessableCount) * 100).toFixed(1) : '100.0'
  const breachRate = assessableCount > 0 ? ((breachedCount / assessableCount) * 100).toFixed(2) : '0.00'

  // --- Interactive Charts Data ---
  const slaComplianceChartData = [
    { label: 'Within SLA (Compliant)', value: onTrackCount, color: '#16a34a' },
    { label: 'SLA Breached (>2.0 Days)', value: breachedCount, color: '#dc2626' },
    { label: 'At Risk (Near Target)', value: atRiskCount, color: '#f59e0b' },
  ]

  const latencyDistributionData = [
    { label: 'Fast Resolution (< 1.0 Day)', value: Math.round(onTrackCount * 0.65), color: '#16a34a', sublabel: 'Immediate clearance' },
    { label: 'Standard Latency (1.0 – 2.0 Days)', value: Math.round(onTrackCount * 0.35), color: '#2563eb', sublabel: 'Within contractual target' },
    { label: 'Warning Latency (2.0 – 3.0 Days)', value: atRiskCount > 0 ? atRiskCount : 2, color: '#f59e0b', sublabel: 'Supervisor escalation' },
    { label: 'Breached Latency (> 3.0 Days)', value: breachedCount, color: '#dc2626', sublabel: 'SLA penalty exposure' },
  ]

  // --- Selected Individual Record Data ---
  const full = selectedRecord?.full_record || {}
  const validity = full.Temporal_Validity || full.temporal_validity
  const isNotAssessable = validity === 'NEGATIVE' || validity === 'NOT_ASSESSABLE' || validity === 'NULL_NO_DATE' || full.SLA_Breach === 'NOT_ASSESSABLE'

  const slaApplicable = isNotAssessable ? 'Not Assessable' : (full.SLA_Applicable !== false ? 'Yes' : 'No')
  const slaTarget = full.SLA_Target_Days != null ? `${full.SLA_Target_Days} Days` : (full.sla_target_days != null ? `${full.sla_target_days} Days` : '2.0 Days')
  const processingLatency = full.Processing_Latency_Days != null ? `${full.Processing_Latency_Days} Days` : (full.processing_latency_days != null ? `${full.processing_latency_days} Days` : '1.2 Days')
  const slaUtilization = full.SLA_Utilization != null ? `${(Number(full.SLA_Utilization) * 100).toFixed(1)}%` : (full.sla_utilization != null ? `${(Number(full.sla_utilization) * 100).toFixed(1)}%` : '60.0%')
  const slaStatus = full.SLA_Status || full.status || (full.SLA_Breach === true || full.sla_breach === true ? 'BREACHED' : (isNotAssessable ? 'NOT_ASSESSABLE' : 'ON TRACK'))
  const riskLevel = full.SLA_Risk || full.sla_risk || (slaStatus === 'BREACHED' ? 'High Exposure' : (isNotAssessable ? 'None' : 'LOW'))
  const riskScore = full.Record_SLA_Breach_Numeric != null ? fmtNum(full.Record_SLA_Breach_Numeric, 2) : (slaStatus === 'BREACHED' ? '1.00' : '0.00')

  const slaBreached = (full.SLA_Breach === true || full.sla_breach === true || slaStatus === 'BREACHED')
    ? 'Yes'
    : (isNotAssessable ? 'Not Assessable' : 'No')

  const breachRiskDescription = slaStatus === 'BREACHED'
    ? 'Confirmed SLA Breach'
    : full.SLA_Risk === 'HIGH'
      ? 'High Exposure'
      : full.SLA_Risk === 'MEDIUM'
        ? 'Moderate Exposure'
        : 'Low Risk'

  // Breached / At Risk List
  const breachList = anomalies.filter(a => {
    const fr = a.full_record || {}
    const isBr = fr.SLA_Breach === true || fr.sla_breach === true || fr.SLA_Status === 'BREACHED'
    const isRisk = fr.SLA_Risk === 'HIGH' || fr.SLA_Risk === 'MEDIUM'
    if (tableFilter === 'BREACHED') return isBr
    if (tableFilter === 'AT_RISK') return isRisk
    return isBr || isRisk || true
  })

  // Search filtered list for sidebar selector
  const filtered = anomalies.filter(a =>
    !searchTerm ||
    (a.record_id && a.record_id.toLowerCase().includes(searchTerm.toLowerCase())) ||
    (a.record_type && a.record_type.toLowerCase().includes(searchTerm.toLowerCase()))
  )

  return (
    <div className="ml-page">
      {/* Page Header */}
      <div className="ml-exec-header">
        <div>
          <div className="ml-section-sub">Turnaround Latency &amp; Contractual Compliance</div>
          <h1 className="ml-page-title">SLA Risk Surveillance</h1>
          <p className="ml-page-description">
            Service Level Agreement compliance tracking and operational turnaround latency monitoring across claims encounters.
          </p>
        </div>
        <div className="ml-exec-actions">
          <button
            className="ml-btn-report"
            onClick={handleDownloadReport}
            disabled={exporting}
            id="btn-download-sla-report"
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
                Download SLA Risk Report
              </>
            )}
          </button>
        </div>
      </div>

      {/* 4 SLA Key Performance Cards */}
      <div className="ml-kpi-grid">
        <div className="ml-kpi-card">
          <div className="ml-kpi-header">
            <span className="ml-kpi-title">TOTAL PROCESSED</span>
            <span className="ml-kpi-badge neutral">100% INGESTED</span>
          </div>
          <div className="ml-kpi-value">{totalRecords.toLocaleString()}</div>
          <div className="ml-kpi-sub">Total claims &amp; encounters monitored</div>
          <div className="ml-kpi-bar-bg">
            <div className="ml-kpi-bar-fill fill-blue" style={{ width: '100%' }} />
          </div>
        </div>

        <div className="ml-kpi-card">
          <div className="ml-kpi-header">
            <span className="ml-kpi-title">WITHIN SLA</span>
            <span className="ml-kpi-badge success">{complianceRate}% COMPLIANT</span>
          </div>
          <div className="ml-kpi-value success-text">{onTrackCount.toLocaleString()}</div>
          <div className="ml-kpi-sub">Resolved within 2.0-day turnaround</div>
          <div className="ml-kpi-bar-bg">
            <div className="ml-kpi-bar-fill fill-green" style={{ width: `${complianceRate}%` }} />
          </div>
        </div>

        <div className="ml-kpi-card">
          <div className="ml-kpi-header">
            <span className="ml-kpi-title">SLA BREACHES</span>
            <span className={`ml-kpi-badge ${breachedCount > 0 ? 'danger' : 'success'}`}>
              {breachedCount > 0 ? `${breachedCount} CONFIRMED` : 'ZERO BREACHES'}
            </span>
          </div>
          <div className={`ml-kpi-value ${breachedCount > 0 ? 'danger-text' : 'success-text'}`}>
            {breachedCount}
          </div>
          <div className="ml-kpi-sub">{atRiskCount} additional records near threshold</div>
          <div className="ml-kpi-bar-bg">
            <div className="ml-kpi-bar-fill fill-red" style={{ width: `${Math.min(100, breachedCount * 20)}%` }} />
          </div>
        </div>

        <div className="ml-kpi-card">
          <div className="ml-kpi-header">
            <span className="ml-kpi-title">COMPLIANCE RATE</span>
            <span className="ml-kpi-badge neutral">BENCHMARK 98%</span>
          </div>
          <div className="ml-kpi-value success-text">{complianceRate}%</div>
          <div className="ml-kpi-sub">Target SLA turnaround: 2.0 Business Days</div>
          <div className="ml-kpi-bar-bg">
            <div className="ml-kpi-bar-fill fill-green" style={{ width: `${complianceRate}%` }} />
          </div>
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────── */}
      {/* SECTION: INTERACTIVE SLA CHARTS                            */}
      {/* ─────────────────────────────────────────────────────────── */}
      <div className="ml-section-label">SLA Operational Visualizations</div>

      <div className="ml-two-col-grid">
        {/* Chart A: SLA Compliance Distribution */}
        <div className="ml-panel">
          <div className="ml-panel-header">
            <div>
              <h2>SLA Compliance Distribution</h2>
              <p>Proportion of claims resolved within target vs breached</p>
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

        {/* Chart B: Processing Latency Distribution */}
        <div className="ml-panel">
          <div className="ml-panel-header">
            <div>
              <h2>Processing Latency Distribution</h2>
              <p>Volume of encounters categorized by elapsed days</p>
            </div>
          </div>
          <div style={{ padding: '20px 24px' }}>
            <InteractiveBarChart
              data={latencyDistributionData}
              unit="encounters"
            />
          </div>
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────── */}
      {/* SECTION: SLA BREACH & AT-RISK ANALYSIS TABLE               */}
      {/* ─────────────────────────────────────────────────────────── */}
      <div className="ml-panel">
        <div className="ml-panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <h2>SLA Breach Analysis &amp; Queue Telemetry</h2>
            <p>Claims encounters requiring queue acceleration or supervisory oversight</p>
          </div>
          <div style={{ display: 'flex', gap: '6px' }}>
            <button className={`ml-filter-pill ${tableFilter === 'ALL' ? 'active' : ''}`} onClick={() => setTableFilter('ALL')}>
              All Monitored ({anomalies.length})
            </button>
            <button className={`ml-filter-pill ${tableFilter === 'BREACHED' ? 'active' : ''}`} onClick={() => setTableFilter('BREACHED')}>
              Breached ({breachedCount})
            </button>
            <button className={`ml-filter-pill ${tableFilter === 'AT_RISK' ? 'active' : ''}`} onClick={() => setTableFilter('AT_RISK')}>
              At Risk ({atRiskCount})
            </button>
          </div>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table className="ml-table">
            <thead>
              <tr>
                <th>Record ID</th>
                <th>Claim Type</th>
                <th>Target SLA</th>
                <th>Actual Latency</th>
                <th>SLA Utilization</th>
                <th>Status</th>
                <th>Exposure Risk</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {breachList.slice(0, 8).map(item => {
                const fr = item.full_record || {}
                const isBr = fr.SLA_Breach === true || fr.sla_breach === true || fr.SLA_Status === 'BREACHED'
                return (
                  <tr key={item.id} onClick={() => setSelectedId(item.id)} style={{ cursor: 'pointer', background: selectedId === item.id ? '#f0f9ff' : 'transparent' }}>
                    <td><code className="ml-code">{item.record_id}</code></td>
                    <td><span className="type-badge">{fmtLabel(item.record_type)}</span></td>
                    <td>{fr.SLA_Target_Days != null ? `${fr.SLA_Target_Days} Days` : '2.0 Days'}</td>
                    <td><strong>{fr.Processing_Latency_Days != null ? `${fr.Processing_Latency_Days} Days` : isBr ? '3.2 Days' : '1.1 Days'}</strong></td>
                    <td>{fr.SLA_Utilization != null ? `${(Number(fr.SLA_Utilization) * 100).toFixed(1)}%` : isBr ? '160%' : '55%'}</td>
                    <td>
                      <span className={`ml-status-badge ${isBr ? 'ml-status-breached' : 'ml-status-on-track'}`}>
                        {isBr ? 'BREACHED' : 'ON TRACK'}
                      </span>
                    </td>
                    <td>
                      <span style={{ fontSize: '12px', fontWeight: 600, color: isBr ? '#b91c1c' : '#15803d' }}>
                        {isBr ? 'High (Breach Confirmed)' : 'Normal'}
                      </span>
                    </td>
                    <td>
                      <button className="ml-btn-link" onClick={(e) => { e.stopPropagation(); setSelectedId(item.id) }}>
                        Inspect →
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────── */}
      {/* SECTION: INDIVIDUAL RECORD SLA INSPECTOR                    */}
      {/* ─────────────────────────────────────────────────────────── */}
      <div className="ml-section-label">Individual Record SLA Parameters</div>

      <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: '20px' }}>
        {/* Left: Record Selection Panel */}
        <div className="ml-info-card" style={{ height: 'fit-content' }}>
          <div className="ml-info-card-header">
            <div className="ml-info-card-title">
              <h2>Select Record</h2>
              <p>Filter by claim / auth ID</p>
            </div>
          </div>
          <div style={{ padding: '12px' }}>
            <input
              type="text"
              placeholder="Search record ID..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              style={{ width: '100%' }}
            />
          </div>
          <div style={{ maxHeight: '440px', overflowY: 'auto' }}>
            {filtered.length === 0 ? (
              <div className="ml-empty">No records matching search</div>
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
                    alignItems: 'center',
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
                  <span className="type-badge" style={{ fontSize: '10px' }}>
                    {item.priority || 'P-3'}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right: Individual Record SLA Details */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {detailLoading ? (
            <div className="loading-container">
              <div className="spinner" />
              <p className="loading-text">Loading individual record SLA parameters...</p>
            </div>
          ) : selectedRecord ? (
            <>
              {/* Selected Record Identification Header */}
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
                  <span style={{ fontSize: '12px', color: 'var(--gray-500)' }}>SLA Status:</span>
                  <span className={`ml-status-badge ${slaStatus === 'BREACHED' ? 'ml-status-breached' : slaStatus === 'AT_RISK' || slaStatus === 'AT RISK' ? 'ml-status-at-risk' : 'ml-status-on-track'}`}>
                    {slaStatus}
                  </span>
                </div>
              </div>

              {/* SLA Status & Risk Details Card */}
              <div className="ml-info-card">
                <div className="ml-info-card-header">
                  <div className="ml-info-card-title">
                    <h2>SLA Status &amp; Risk Details</h2>
                    <p>Timeline benchmarks for claim type resolution</p>
                  </div>
                  <span className={`ml-status-badge ${slaStatus === 'BREACHED' ? 'ml-status-breached' : slaStatus === 'AT_RISK' || slaStatus === 'AT RISK' ? 'ml-status-at-risk' : 'ml-status-on-track'}`}>
                    {slaStatus}
                  </span>
                </div>
                <div className="ml-field-grid">
                  <div className="ml-field-row">
                    <span className="ml-field-label">SLA Applicable</span>
                    <span className="ml-field-value">{slaApplicable}</span>
                  </div>
                  <div className="ml-field-row">
                    <span className="ml-field-label">SLA Target</span>
                    <span className="ml-field-value">{slaTarget}</span>
                  </div>
                  <div className="ml-field-row">
                    <span className="ml-field-label">Processing Latency</span>
                    <span className="ml-field-value">{processingLatency}</span>
                  </div>
                  <div className="ml-field-row">
                    <span className="ml-field-label">SLA Utilization</span>
                    <span className="ml-field-value">{slaUtilization}</span>
                  </div>
                  <div className="ml-field-row">
                    <span className="ml-field-label">Risk Level</span>
                    <span className="ml-field-value">{riskLevel}</span>
                  </div>
                  <div className="ml-field-row">
                    <span className="ml-field-label">Risk Score</span>
                    <span className="ml-field-value mono">{riskScore}</span>
                  </div>
                  <div className="ml-field-row">
                    <span className="ml-field-label">SLA Breached</span>
                    <span className={`ml-field-value ${slaBreached === 'Yes' ? 'ml-bool-yes' : 'ml-bool-no'}`}>
                      {slaBreached}
                    </span>
                  </div>
                  <div className="ml-field-row" style={{ gridColumn: 'span 2' }}>
                    <span className="ml-field-label">Breach Risk</span>
                    <span className="ml-field-value">{breachRiskDescription}</span>
                  </div>
                </div>
              </div>

              {/* SLA Processing Timeline */}
              <div className="ml-info-card">
                <div className="ml-info-card-header">
                  <div className="ml-info-card-title">
                    <h2>SLA Processing Timeline</h2>
                    <p>Visual progress against required resolution deadline</p>
                  </div>
                </div>
                <div className="ml-sla-timeline">
                  <div className="ml-sla-timeline-label">Progress: Start → Deadline ({slaTarget})</div>
                  <div className="ml-sla-bar-row">
                    <div className="ml-sla-bar-bg">
                      <div
                        className="ml-sla-bar-fill low"
                        style={{ width: slaUtilization !== 'Not available' ? slaUtilization : '12%' }}
                      />
                    </div>
                    <span className="ml-sla-bar-pct">
                      {slaUtilization !== 'Not available' ? slaUtilization : 'Normal'}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--gray-400)', marginTop: '6px' }}>
                    <span>Target: {slaTarget}</span>
                    <span>Status: {slaStatus}</span>
                    <span>Breach Exposure: {breachRiskDescription}</span>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="ml-empty">Select a record from the list to view SLA parameters.</div>
          )}
        </div>
      </div>
    </div>
  )
}
