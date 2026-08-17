import React, { useEffect, useState } from 'react'
import { getAnomalyDetail } from '../services/api'
import './AnomalyDetail.css'

export default function AnomalyDetail({ anomaly, onClose }) {
  const [detail, setDetail] = useState(anomaly)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)

  // Load full detail if needed
  useEffect(() => {
    if (!anomaly.full_record) {
      setIsLoading(true)
      getAnomalyDetail(anomaly.id)
        .then(data => setDetail(data))
        .catch(err => setError(err.message))
        .finally(() => setIsLoading(false))
    }
  }, [anomaly.id])

  const getSeverityColor = (severity) => {
    const colors = {
      HIGH: '#d32f2f',
      MEDIUM: '#f57c00',
      LOW: '#388e3c',
    }
    return colors[severity] || '#999'
  }

  return (
    <div className="detail-overlay" onClick={onClose}>
      <div className="detail-modal" onClick={(e) => e.stopPropagation()}>
        <div className="detail-header">
          <div className="detail-title">
            <h2>Anomaly Details</h2>
            <span className="detail-id">{detail.record_id}</span>
          </div>
          <button className="close-button" onClick={onClose} title="Close">
            ✕
          </button>
        </div>

        {isLoading && (
          <div className="detail-loading">
            <div className="spinner"></div>
            <p>Loading details...</p>
          </div>
        )}

        {error && (
          <div className="detail-error">
            <p>⚠️ {error}</p>
          </div>
        )}

        {!isLoading && !error && (
          <div className="detail-content">
            {/* Key Information */}
            <section className="detail-section">
              <h3>Key Information</h3>
              <div className="info-grid">
                <div className="info-item">
                  <span className="info-label">Record ID</span>
                  <span className="info-value code">{detail.record_id}</span>
                </div>
                <div className="info-item">
                  <span className="info-label">Record Type</span>
                  <span className="info-value">{detail.record_type}</span>
                </div>
                <div className="info-item">
                  <span className="info-label">Severity</span>
                  <span
                    className="info-value"
                    style={{ color: getSeverityColor(detail.severity) }}
                  >
                    <strong>{detail.severity}</strong>
                  </span>
                </div>
                <div className="info-item">
                  <span className="info-label">Priority</span>
                  <span className="info-value">{detail.priority}</span>
                </div>
                <div className="info-item">
                  <span className="info-label">Anomaly Type</span>
                  <span className="info-value">{detail.anomaly_type || '—'}</span>
                </div>
                <div className="info-item">
                  <span className="info-label">Confidence</span>
                  <span className="info-value">
                    {detail.confidence ? (detail.confidence * 100).toFixed(0) : '—'}%
                  </span>
                </div>
              </div>
            </section>

            {/* Primary Signal */}
            {detail.primary_signal && (
              <section className="detail-section">
                <h3>Why Was This Flagged?</h3>
                <div className="signal-box">
                  <p>{detail.primary_signal}</p>
                </div>
              </section>
            )}

            {/* Root Cause */}
            {detail.likely_root_cause && (
              <section className="detail-section">
                <h3>Likely Root Cause</h3>
                <div className="root-cause-box">
                  <p>{detail.likely_root_cause}</p>
                </div>
              </section>
            )}

            {/* Recommended Action */}
            {detail.recommended_action && (
              <section className="detail-section">
                <h3>Recommended Action</h3>
                <div className="action-box">
                  <p>{detail.recommended_action}</p>
                </div>
              </section>
            )}

            {/* Impact */}
            {detail.impact && (
              <section className="detail-section">
                <h3>Business Impact</h3>
                <div className="impact-box">
                  <p>{detail.impact}</p>
                </div>
              </section>
            )}

            {/* Additional Checks */}
            {detail.additional_checks && (
              <section className="detail-section">
                <h3>Additional Checks Required</h3>
                <div className="checks-box">
                  <p>{detail.additional_checks}</p>
                </div>
              </section>
            )}

            {/* Technical Details */}
            {detail.full_record && (
              <section className="detail-section">
                <h3>Technical Details</h3>
                <div className="technical-details">
                  <pre>{JSON.stringify(detail.full_record, null, 2)}</pre>
                </div>
              </section>
            )}
          </div>
        )}

        <div className="detail-footer">
          <button className="close-footer-button" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
