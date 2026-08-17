import React from 'react'
import './AnomaliesTable.css'

export default function AnomaliesTable({ anomalies, onSelectAnomaly }) {
  const getSeverityClass = (severity) => {
    return `severity-${severity.toLowerCase()}`
  }

  const getPriorityClass = (priority) => {
    return `priority-${priority.toLowerCase().replace(' ', '-')}`
  }

  return (
    <div className="anomalies-table-container">
      <table className="anomalies-table">
        <thead>
          <tr>
            <th className="col-priority">Priority</th>
            <th className="col-record-id">Record ID</th>
            <th className="col-type">Type</th>
            <th className="col-severity">Severity</th>
            <th className="col-anomaly">Anomaly Type</th>
            <th className="col-signal">Primary Signal</th>
            <th className="col-confidence">Confidence</th>
            <th className="col-action">Action</th>
          </tr>
        </thead>
        <tbody>
          {anomalies.map((anomaly) => (
            <tr key={anomaly.id} className="anomaly-row">
              <td className="col-priority">
                <span className={`priority-badge ${getPriorityClass(anomaly.priority)}`}>
                  {anomaly.priority}
                </span>
              </td>
              <td className="col-record-id">
                <code className="record-id-code">{anomaly.record_id}</code>
              </td>
              <td className="col-type">
                <span className="type-badge">{anomaly.record_type}</span>
              </td>
              <td className="col-severity">
                <span className={`severity-badge ${getSeverityClass(anomaly.severity)}`}>
                  {anomaly.severity}
                </span>
              </td>
              <td className="col-anomaly">{anomaly.anomaly_type || '—'}</td>
              <td className="col-signal">
                <span className="signal-text" title={anomaly.primary_signal}>
                  {anomaly.primary_signal ? anomaly.primary_signal.substring(0, 50) + '...' : '—'}
                </span>
              </td>
              <td className="col-confidence">
                <span className="confidence-value">
                  {anomaly.confidence ? (anomaly.confidence * 100).toFixed(0) : '0'}%
                </span>
              </td>
              <td className="col-action">
                <button
                  className="view-button"
                  onClick={() => onSelectAnomaly(anomaly)}
                  title="View details"
                >
                  View
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
