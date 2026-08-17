import React, { useState } from 'react'
import { useMedlyticsData } from '../../hooks/useMedlyticsData'
import { statusClass, fmtLabel, fmtNum, fmtPct, fmtBool } from '../../utils/statusUtils'
import AnomalyDetail from '../AnomalyDetail'
import './shared-pages.css'

export default function OverviewPage() {
  const { anomalies, statistics, isLoading, error, currentRun } = useMedlyticsData()
  const [selectedAnomaly, setSelectedAnomaly] = useState(null)

  if (isLoading) {
    return (
      <div className="loading-container">
        <div className="spinner" />
        <p className="loading-text">Loading Overview Monitoring Data...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="error-banner" role="alert">
        <span>Unable to load monitoring data. Please check the backend connection.</span>
      </div>
    )
  }

  const sev = currentRun?.severity_summary || statistics?.by_severity || {}
  const totalAnomalies = currentRun?.total_anomalies ?? statistics?.total_anomalies ?? anomalies.length
  const totalRecords = currentRun?.total_records ?? statistics?.total_records ?? 0
  const dqScore = statistics?.overall_data_quality_score
  const overallRisk = statistics?.overall_risk_level || 'NORMAL'

  return (
    <div className="ml-page">
      <div className="ml-page-heading">
        <h1>Monitoring Overview</h1>
        <p>High-level operational health across Anomaly Detection, SLA Risk, and Data Quality.</p>
      </div>

      <div className="ml-section-label">Overall Monitoring Summary</div>

      {/* Independent 3-pillar summary */}
      <div className="ml-summary-trio">
        {/* Pillar 1: Anomaly Status */}
        <div className="ml-summary-card anomaly">
          <span className="ml-summary-card-label">Anomaly Status</span>
          <div className="ml-summary-card-status">
            <span className={`ml-status-badge ${totalAnomalies > 0 ? 'ml-status-anomalous' : 'ml-status-normal'}`}>
              {totalAnomalies > 0 ? 'ANOMALOUS' : 'NORMAL'}
            </span>
          </div>
          <span className="ml-summary-card-desc">
            {totalAnomalies.toLocaleString()} anomalies flagged in {totalRecords.toLocaleString()} records
          </span>
        </div>

        {/* Pillar 2: SLA Risk Status */}
        <div className="ml-summary-card sla">
          <span className="ml-summary-card-label">SLA Risk Status</span>
          <div className="ml-summary-card-status">
            <span className="ml-status-badge ml-status-at-risk">
              {overallRisk ? overallRisk.toUpperCase() : 'MONITORED'}
            </span>
          </div>
          <span className="ml-summary-card-desc">
            Population SLA monitoring active
          </span>
        </div>

        {/* Pillar 3: Data Quality Status */}
        <div className="ml-summary-card quality">
          <span className="ml-summary-card-label">Data Quality Status</span>
          <div className="ml-summary-card-status">
            <span className={`ml-status-badge ${dqScore != null && dqScore < 80 ? 'ml-status-warning' : 'ml-status-pass'}`}>
              {dqScore != null ? (dqScore >= 80 ? 'PASS' : 'WARNING') : 'PASS'}
            </span>
          </div>
          <span className="ml-summary-card-desc">
            {dqScore != null ? `Quality Score: ${fmtNum(dqScore, 1)} / 100` : 'Data validity & schema checked'}
          </span>
        </div>
      </div>

      {/* KPI metrics strip */}
      <div className="ml-section-label">Key Operational Indicators</div>
      <div className="ml-kpi-strip">
        <div className="ml-kpi-tile">
          <span className="ml-kpi-tile-label">Total Records</span>
          <span className="ml-kpi-tile-value">{totalRecords.toLocaleString()}</span>
          <span className="ml-kpi-tile-sub">Input dataset</span>
        </div>
        <div className="ml-kpi-tile">
          <span className="ml-kpi-tile-label">Total Anomalies</span>
          <span className="ml-kpi-tile-value">{totalAnomalies.toLocaleString()}</span>
          <span className="ml-kpi-tile-sub">ML flagged</span>
        </div>
        <div className="ml-kpi-tile">
          <span className="ml-kpi-tile-label">High Severity</span>
          <span className="ml-kpi-tile-value text-danger">{(sev.high || 0).toLocaleString()}</span>
          <span className="ml-kpi-tile-sub">Priority 1 / 2</span>
        </div>
        <div className="ml-kpi-tile">
          <span className="ml-kpi-tile-label">Medium Severity</span>
          <span className="ml-kpi-tile-value text-warning">{(sev.medium || 0).toLocaleString()}</span>
          <span className="ml-kpi-tile-sub">Priority 3</span>
        </div>
        <div className="ml-kpi-tile">
          <span className="ml-kpi-tile-label">Low Severity</span>
          <span className="ml-kpi-tile-value text-success">{(sev.low || 0).toLocaleString()}</span>
          <span className="ml-kpi-tile-sub">Priority 4</span>
        </div>
        {dqScore != null && (
          <div className="ml-kpi-tile">
            <span className="ml-kpi-tile-label">Data Quality Score</span>
            <span className="ml-kpi-tile-value">{fmtNum(dqScore, 1)}</span>
            <span className="ml-kpi-tile-sub">Out of 100</span>
          </div>
        )}
      </div>

      {/* Recent Monitored Records Table */}
      <div className="ml-section-label">Active Monitored Records</div>
      <div className="ml-info-card">
        <div className="ml-info-card-header">
          <div className="ml-info-card-title">
            <h2>Monitored Records Summary</h2>
            <p>Recent records analyzed by the ML and monitoring pipelines</p>
          </div>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table className="anomalies-table" style={{ width: '100%', minWidth: '700px' }}>
            <thead>
              <tr>
                <th style={{ padding: '10px 14px' }}>Record ID</th>
                <th style={{ padding: '10px 14px' }}>Record Type</th>
                <th style={{ padding: '10px 14px' }}>Severity</th>
                <th style={{ padding: '10px 14px' }}>Anomaly Type</th>
                <th style={{ padding: '10px 14px' }}>Primary Signal</th>
                <th style={{ padding: '10px 14px', textAlign: 'center' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {anomalies.slice(0, 10).map(rec => (
                <tr key={rec.id}>
                  <td style={{ padding: '10px 14px' }}>
                    <code className="record-id-code">{rec.record_id}</code>
                  </td>
                  <td style={{ padding: '10px 14px' }}>
                    <span className="type-badge">{fmtLabel(rec.record_type)}</span>
                  </td>
                  <td style={{ padding: '10px 14px' }}>
                    <span className={`severity-badge severity-${(rec.severity || '').toLowerCase()}`}>
                      {rec.severity}
                    </span>
                  </td>
                  <td style={{ padding: '10px 14px' }}>{rec.anomaly_type || '—'}</td>
                  <td style={{ padding: '10px 14px', maxWidth: '240px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={rec.primary_signal || ''}>
                    {rec.primary_signal || '—'}
                  </td>
                  <td style={{ padding: '10px 14px', textAlign: 'center' }}>
                    <button className="view-button" onClick={() => setSelectedAnomaly(rec)}>
                      Inspect
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {selectedAnomaly && (
        <AnomalyDetail anomaly={selectedAnomaly} onClose={() => setSelectedAnomaly(null)} />
      )}
    </div>
  )
}
