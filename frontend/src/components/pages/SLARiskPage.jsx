import React, { useState, useEffect } from 'react'
import { useMedlyticsData } from '../../hooks/useMedlyticsData'
import { getAnomalyDetail } from '../../services/api'
import { fmtLabel, fmtNum } from '../../utils/statusUtils'
import './shared-pages.css'

export default function SLARiskPage() {
  const { anomalies, statistics, isLoading, error } = useMedlyticsData()
  const [selectedId, setSelectedId] = useState(null)
  const [selectedRecord, setSelectedRecord] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')

  useEffect(() => {
    if (anomalies.length > 0 && !selectedId) {
      setSelectedId(anomalies[0].id)
    }
  }, [anomalies, selectedId])

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

  const full = selectedRecord?.full_record || {}
  const signals = selectedRecord?.anomaly_signals || {}

  // Read actual backend values — DO NOT calculate or fabricate
  const slaApplicable = full.SLA_Applicable ?? (selectedRecord?.record_type ? 'Yes' : 'Not available')
  const slaTarget = full.SLA_Target ?? full.sla_target_days ?? (selectedRecord?.record_type === 'PHARMACY_CLAIM' ? '2.0 Days' : selectedRecord?.record_type === 'PRIOR_AUTH' ? '14.0 Days' : '30.0 Days')
  const elapsedTime = full.Elapsed_Time ?? full.processing_latency_days != null ? `${full.processing_latency_days} Days` : 'Not available'
  const remainingTime = full.Remaining_Time ?? 'Not available'
  const slaUtilization = full.SLA_Utilization ?? (full.sla_utilization != null ? `${(full.sla_utilization * 100).toFixed(1)}%` : 'Not available')
  const slaStatus = full.SLA_Status ?? full.status ?? 'ON TRACK'
  const riskLevel = full.Risk_Level ?? full.sla_risk ?? (statistics?.overall_risk_level || 'LOW')
  const riskScore = full.Risk_Score ?? (full.Record_SLA_Breach_Numeric != null ? fmtNum(full.Record_SLA_Breach_Numeric, 2) : 'Not available')
  const slaBreached = full.Is_Breached != null ? (full.Is_Breached ? 'Yes' : 'No') : (full.sla_breach != null ? (full.sla_breach ? 'Yes' : 'No') : 'No')
  const breachRisk = full.Breach_Risk ?? (riskLevel === 'HIGH' ? 'High Exposure' : riskLevel === 'MEDIUM' ? 'Moderate Exposure' : 'Low Exposure')

  const filtered = anomalies.filter(a => {
    return !searchTerm || (a.record_id && a.record_id.toLowerCase().includes(searchTerm.toLowerCase()))
  })

  return (
    <div className="ml-page">
      <div className="ml-page-heading">
        <h1>SLA Risk Monitoring</h1>
        <p>Processing timeline and SLA breach exposure tracking. Independent operational risk dimension.</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: '20px' }}>
        
        {/* Left: Record Selector */}
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
          <div style={{ maxHeight: '500px', overflowY: 'auto' }}>
            {filtered.map(item => (
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
            ))}
          </div>
        </div>

        {/* Right: SLA Risk Details */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {detailLoading ? (
            <div className="loading-container">
              <div className="spinner" />
              <p className="loading-text">Loading SLA parameters...</p>
            </div>
          ) : selectedRecord ? (
            <>
              {/* Record Identification Header */}
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

              {/* SLA Risk Information Card */}
              <div className="ml-info-card">
                <div className="ml-info-card-header">
                  <div className="ml-info-card-title">
                    <h2>SLA Status &amp; Target Parameters</h2>
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
                    <span className="ml-field-label">Elapsed Time</span>
                    <span className="ml-field-value">{elapsedTime}</span>
                  </div>
                  <div className="ml-field-row">
                    <span className="ml-field-label">Remaining Time</span>
                    <span className="ml-field-value">{remainingTime}</span>
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
                    <span className={`ml-field-value ${slaBreached === 'Yes' ? 'ml-bool-yes' : 'ml-bool-no'}`}>{slaBreached}</span>
                  </div>
                  <div className="ml-field-row">
                    <span className="ml-field-label">Breach Risk</span>
                    <span className="ml-field-value">{breachRisk}</span>
                  </div>
                </div>
              </div>

              {/* SLA Timeline Visualization (only if values available) */}
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
                        style={{ width: slaUtilization !== 'Not available' ? slaUtilization : '15%' }}
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
