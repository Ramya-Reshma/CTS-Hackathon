import React from 'react'
import './SummaryCards.css'

export default function SummaryCards({ totalRecords, totalAnomalies, severitySummary, overallDataQualityScore }) {
  return (
    <div className="summary-cards">
      <div className="card">
        <div className="card-label">Total Records</div>
        <div className="card-value">{totalRecords.toLocaleString()}</div>
      </div>

      <div className="card">
        <div className="card-label">Total Anomalies</div>
        <div className="card-value">{totalAnomalies.toLocaleString()}</div>
      </div>

      {overallDataQualityScore !== undefined && overallDataQualityScore !== null && (
        <div className="card">
          <div className="card-label">Overall Data Quality</div>
          <div className="card-value">{Number(overallDataQualityScore).toFixed(1)} / 100</div>
        </div>
      )}

      <div className="card card-high">
        <div className="card-label">High Severity</div>
        <div className="card-value">{(severitySummary.high || 0).toLocaleString()}</div>
      </div>

      <div className="card card-medium">
        <div className="card-label">Medium Severity</div>
        <div className="card-value">{(severitySummary.medium || 0).toLocaleString()}</div>
      </div>

      <div className="card card-low">
        <div className="card-label">Low Severity</div>
        <div className="card-value">{(severitySummary.low || 0).toLocaleString()}</div>
      </div>
    </div>
  )
}
