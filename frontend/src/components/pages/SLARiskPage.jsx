import React, { useState, useEffect } from 'react'
import { useMedlyticsData } from '../../hooks/useMedlyticsData'
import { getAnomalyDetail } from '../../services/api'
import { fmtLabel, fmtNum, fmtPct } from '../../utils/statusUtils'
import './shared-pages.css'

export default function SLARiskPage() {
  const { anomalies, statistics, isLoading, error, currentRun } = useMedlyticsData()
  const [selectedId, setSelectedId] = useState(null)
  const [selectedRecord, setSelectedRecord] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')

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

  // --- OVERALL POPULATION SLA METRICS (from backend SLA Engine) ---
  const slaSummary = statistics?.sla_summary || null
  const totalRecords = slaSummary?.total_records ?? currentRun?.total_records ?? statistics?.total_records ?? anomalies.length
  const assessableCount = slaSummary?.records_assessable ?? (totalRecords - (slaSummary?.records_not_assessable ?? 0))
  const notAssessableCount = slaSummary?.records_not_assessable ?? 0
  const breachedCount = slaSummary?.records_breached ?? anomalies.filter(a => {
    const fr = a.full_record || {}
    return fr.SLA_Breach === true || fr.sla_breach === true || fr.SLA_Status === 'BREACHED'
  }).length
  const atRiskCount = slaSummary?.records_at_risk ?? 0
  const onTrackCount = slaSummary?.records_normal ?? Math.max(0, assessableCount - breachedCount - atRiskCount)

  const complianceRate = assessableCount > 0 ? (onTrackCount / assessableCount) * 100 : 100
  const breachRate = assessableCount > 0 ? (breachedCount / assessableCount) * 100 : 0

  // --- INDIVIDUAL SELECTED RECORD METRICS ---
  const full = selectedRecord?.full_record || {}
  const validity = full.Temporal_Validity || full.temporal_validity
  const isNotAssessable = validity === 'NEGATIVE' || validity === 'NOT_ASSESSABLE' || validity === 'NULL_NO_DATE' || full.SLA_Breach === 'NOT_ASSESSABLE'

  const slaApplicable = isNotAssessable ? 'Not Assessable' : (full.SLA_Applicable !== false ? 'Yes' : 'No')
  const slaTarget = full.SLA_Target_Days != null ? `${full.SLA_Target_Days} Days` : (full.sla_target_days != null ? `${full.sla_target_days} Days` : 'Not available')
  const processingLatency = full.Processing_Latency_Days != null ? `${full.Processing_Latency_Days} Days` : (full.processing_latency_days != null ? `${full.processing_latency_days} Days` : 'Not available')
  const slaUtilization = full.SLA_Utilization != null ? `${(Number(full.SLA_Utilization) * 100).toFixed(1)}%` : (full.sla_utilization != null ? `${(Number(full.sla_utilization) * 100).toFixed(1)}%` : 'Not available')
  const slaStatus = full.SLA_Status || full.status || (full.SLA_Breach === true || full.sla_breach === true ? 'BREACHED' : (isNotAssessable ? 'NOT_ASSESSABLE' : 'NORMAL'))
  const riskLevel = full.SLA_Risk || full.sla_risk || (slaStatus === 'BREACHED' ? 'None (Breached)' : (isNotAssessable ? 'None (Not Assessable)' : 'LOW'))
  const riskScore = full.Record_SLA_Breach_Numeric != null ? fmtNum(full.Record_SLA_Breach_Numeric, 2) : (slaStatus === 'BREACHED' ? '1.00' : '0.00')
  
  // Strictly check actual breach status for individual record
  const slaBreached = (full.SLA_Breach === true || full.sla_breach === true || slaStatus === 'BREACHED')
    ? 'Yes'
    : (isNotAssessable ? 'Not Assessable' : 'No')
    
  const breachRisk = full.SLA_Risk === 'HIGH'
    ? 'High Exposure'
    : full.SLA_Risk === 'MEDIUM'
      ? 'Moderate Exposure'
      : (slaStatus === 'BREACHED' ? 'Confirmed Breach' : (isNotAssessable ? 'Not Assessable' : 'Low Exposure'))

  const filtered = anomalies.filter(a => {
    return !searchTerm || (a.record_id && a.record_id.toLowerCase().includes(searchTerm.toLowerCase()))
  })

  return (
    <div className="ml-page">
      {/* Page Header */}
      <div className="ml-page-heading">
        <h1>SLA Risk</h1>
        <p>Processing timeline, SLA exposure, and breach monitoring across the entire claims population and individual records.</p>
      </div>

      {/* ─────────────────────────────────────────────────────────── */}
      {/* SECTION 1: OVERALL SLA RISK SUMMARY (POPULATION LEVEL)    */}
      {/* ─────────────────────────────────────────────────────────── */}
      <div className="ml-section-label">Overall SLA Risk Summary</div>

      <div className="ml-kpi-strip" style={{ gridTemplateColumns: 'repeat(6, 1fr)' }}>
        <div className="ml-kpi-tile">
          <span className="ml-kpi-tile-label">Total Records</span>
          <span className="ml-kpi-tile-value">{totalRecords.toLocaleString()}</span>
          <span className="ml-kpi-tile-sub">Monitored population</span>
        </div>
        <div className="ml-kpi-tile">
          <span className="ml-kpi-tile-label">Assessable</span>
          <span className="ml-kpi-tile-value" style={{ color: 'var(--navy-800)' }}>{assessableCount.toLocaleString()}</span>
          <span className="ml-kpi-tile-sub">Valid timestamps</span>
        </div>
        <div className="ml-kpi-tile">
          <span className="ml-kpi-tile-label">On Track / Normal</span>
          <span className="ml-kpi-tile-value text-success">{onTrackCount.toLocaleString()}</span>
          <span className="ml-kpi-tile-sub">Within SLA latency</span>
        </div>
        <div className="ml-kpi-tile">
          <span className="ml-kpi-tile-label">At Risk</span>
          <span className="ml-kpi-tile-value text-warning">{atRiskCount.toLocaleString()}</span>
          <span className="ml-kpi-tile-sub">Process shift detected</span>
        </div>
        <div className="ml-kpi-tile">
          <span className="ml-kpi-tile-label">Breached</span>
          <span className="ml-kpi-tile-value text-danger">{breachedCount.toLocaleString()}</span>
          <span className="ml-kpi-tile-sub">Confirmed SLA breaches</span>
        </div>
        <div className="ml-kpi-tile">
          <span className="ml-kpi-tile-label">Not Assessable</span>
          <span className="ml-kpi-tile-value" style={{ color: 'var(--gray-500)' }}>{notAssessableCount.toLocaleString()}</span>
          <span className="ml-kpi-tile-sub">Missing / negative date</span>
        </div>
      </div>

      {/* SLA Compliance / Risk Overview Card */}
      <div className="ml-info-card" style={{ marginTop: '12px' }}>
        <div className="ml-info-card-header">
          <div className="ml-info-card-title">
            <h2>SLA Compliance &amp; Population Risk Overview</h2>
            <p>Overall operational health and contractual compliance across current run</p>
          </div>
        </div>
        <div className="ml-field-grid">
          <div className="ml-field-row">
            <span className="ml-field-label">SLA Compliance Rate</span>
            <span className="ml-field-value text-success">{fmtPct(complianceRate)}</span>
          </div>
          <div className="ml-field-row">
            <span className="ml-field-label">SLA Breach Rate</span>
            <span className={`ml-field-value ${breachedCount > 0 ? 'text-danger' : 'text-success'}`}>{fmtPct(breachRate)}</span>
          </div>
          <div className="ml-field-row">
            <span className="ml-field-label">High Risk Records</span>
            <span className="ml-field-value text-danger">{atRiskCount.toLocaleString()}</span>
          </div>
          <div className="ml-field-row">
            <span className="ml-field-label">Medium Risk Records</span>
            <span className="ml-field-value text-warning">0</span>
          </div>
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────── */}
      {/* SECTION 2: RECORD UNDER MONITORING (INDIVIDUAL LEVEL)      */}
      {/* ─────────────────────────────────────────────────────────── */}
      <div className="ml-section-label" style={{ marginTop: '16px' }}>Record Under Monitoring</div>

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
          <div style={{ maxHeight: '480px', overflowY: 'auto' }}>
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
                    <span className="ml-field-value">{breachRisk}</span>
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
                    <span>Breach Exposure: {breachRisk}</span>
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
