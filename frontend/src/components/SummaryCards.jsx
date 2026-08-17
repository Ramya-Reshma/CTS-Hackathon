import React from 'react'
import './SummaryCards.css'

export default function SummaryCards({ totalRecords, totalAnomalies, severitySummary, overallDataQualityScore }) {
  return (
    <div className="summary-cards">

      <div className="kpi-card">
        <span className="kpi-label">Total Records</span>
        <span className="kpi-value">{(totalRecords || 0).toLocaleString()}</span>
        <span className="kpi-sub">Analysis dataset</span>
      </div>

      <div className="kpi-card">
        <span className="kpi-label">Total Anomalies</span>
        <span className="kpi-value">{(totalAnomalies || 0).toLocaleString()}</span>
        <span className="kpi-sub">Detected by ML pipeline</span>
      </div>

      {overallDataQualityScore != null && (
        <div className="kpi-card kpi-dq">
          <span className="kpi-label">Data Quality</span>
          <span className="kpi-value">{Number(overallDataQualityScore).toFixed(1)}</span>
          <span className="kpi-sub">Score out of 100</span>
        </div>
      )}

      <div className="kpi-card kpi-high">
        <span className="kpi-label">High</span>
        <span className="kpi-value">{((severitySummary || {}).high || 0).toLocaleString()}</span>
        <span className="kpi-sub">Severity anomalies</span>
      </div>

      <div className="kpi-card kpi-medium">
        <span className="kpi-label">Medium</span>
        <span className="kpi-value">{((severitySummary || {}).medium || 0).toLocaleString()}</span>
        <span className="kpi-sub">Severity anomalies</span>
      </div>

      <div className="kpi-card kpi-low">
        <span className="kpi-label">Low</span>
        <span className="kpi-value">{((severitySummary || {}).low || 0).toLocaleString()}</span>
        <span className="kpi-sub">Severity anomalies</span>
      </div>

    </div>
  )
}
