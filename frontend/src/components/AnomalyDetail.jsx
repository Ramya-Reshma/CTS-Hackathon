import React, { useEffect, useState } from 'react'
import { getAnomalyDetail } from '../services/api'
import { formatRecommendations } from '../utils/recommendationFormatter'
import './AnomalyDetail.css'

// Severity badge helpers (presentation only — no logic change)
const getSevClass = (s) => {
  const m = { HIGH: 'severity-high', MEDIUM: 'severity-medium', LOW: 'severity-low' }
  return m[s] || 'severity-badge'
}

export default function AnomalyDetail({ anomaly, onClose }) {
  const [detail, setDetail] = useState(anomaly)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)

  // Load full detail if needed — unchanged logic
  useEffect(() => {
    if (!anomaly.full_record) {
      setIsLoading(true)
      getAnomalyDetail(anomaly.id)
        .then(data => setDetail(data))
        .catch(err => setError(err.message))
        .finally(() => setIsLoading(false))
    }
  }, [anomaly.id])

  return (
    <div className="detail-overlay" onClick={onClose} role="dialog" aria-modal="true" aria-label="Anomaly Details">
      <div className="detail-modal" onClick={(e) => e.stopPropagation()}>

        {/* ── Header ───────────────────────────────────────── */}
        <div className="detail-header">
          <div className="detail-title">
            <span className="detail-header-label">Record Investigation</span>
            <span className="detail-record-id">{detail.record_id}</span>
            <div className="detail-severity-row">
              <span className={`severity-badge ${getSevClass(detail.severity)}`}>{detail.severity}</span>
            </div>
          </div>
          <button className="close-button" onClick={onClose} aria-label="Close panel">✕</button>
        </div>

        {/* ── Meta strip ───────────────────────────────────── */}
        <div className="detail-meta">
          <div className="detail-meta-item">
            <span className="detail-meta-label">Record Type</span>
            <span className="detail-meta-value">{detail.record_type || '—'}</span>
          </div>
          <div className="detail-meta-item">
            <span className="detail-meta-label">Priority</span>
            <span className="detail-meta-value">{detail.priority || '—'}</span>
          </div>
          <div className="detail-meta-item">
            <span className="detail-meta-label">Anomaly Type</span>
            <span className="detail-meta-value">{detail.anomaly_type || '—'}</span>
          </div>
          <div className="detail-meta-item">
            <span className="detail-meta-label">Confidence</span>
            <span className="detail-meta-value">
              {detail.confidence ? `${(detail.confidence * 100).toFixed(0)}%` : '—'}
            </span>
          </div>
        </div>

        {/* ── Loading / Error ───────────────────────────────── */}
        {isLoading && (
          <div className="detail-loading">
            <div className="spinner" />
            <span>Loading details...</span>
          </div>
        )}

        {error && (
          <div className="detail-error">
            <p>⚠ {error}</p>
          </div>
        )}

        {!isLoading && !error && (
          <div className="detail-content">

            {/* Primary Signal */}
            {detail.primary_signal && (
              <div className="detail-section">
                <h3>Why Was This Flagged?</h3>
                <div className="signal-box">
                  <p>{detail.primary_signal}</p>
                </div>
              </div>
            )}

            {/* Root Cause */}
            {detail.likely_root_cause && (
              <div className="detail-section">
                <h3>Likely Root Cause</h3>
                <div className="root-cause-box">
                  <p>{detail.likely_root_cause}</p>
                </div>
              </div>
            )}

            {/* Recommended Action */}
            <div className="detail-section">
              <h3>Recommended Action</h3>
              <div className="action-box">
                <ul className="ml-rec-bullet-list">
                  {formatRecommendations(detail.recommended_action, {
                    isAnomalous: detail.severity === 'HIGH' || detail.severity === 'MEDIUM',
                    severity: detail.severity,
                    anomaly_type: detail.anomaly_type
                  }).map((action, idx) => (
                    <li key={idx} className="ml-rec-bullet-item">
                      {action}
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Business Impact */}
            {detail.impact && (
              <div className="detail-section">
                <h3>Business Impact</h3>
                <div className="impact-box">
                  <p>{detail.impact}</p>
                </div>
              </div>
            )}

            {/* Additional Checks */}
            {detail.additional_checks && (
              <div className="detail-section">
                <h3>Additional Checks Required</h3>
                <div className="checks-box">
                  <p>{detail.additional_checks}</p>
                </div>
              </div>
            )}

            {/* Evidence */}
            {Array.isArray(detail.evidence) && detail.evidence.length > 0 && (
              <div className="detail-section">
                <h3>Evidence</h3>
                <div className="checks-box">
                  <ul>{detail.evidence.map((item, i) => <li key={`ev-${i}`}>{item}</li>)}</ul>
                </div>
              </div>
            )}

            {/* Observed Facts */}
            {Array.isArray(detail.observed_facts) && detail.observed_facts.length > 0 && (
              <div className="detail-section">
                <h3>Observed Facts</h3>
                <div className="checks-box">
                  <ul>{detail.observed_facts.map((item, i) => <li key={`of-${i}`}>{item}</li>)}</ul>
                </div>
              </div>
            )}

            {/* Possible Causes */}
            {Array.isArray(detail.possible_causes) && detail.possible_causes.length > 0 && (
              <div className="detail-section">
                <h3>Possible Causes</h3>
                <div className="checks-box">
                  <ul>{detail.possible_causes.map((item, i) => <li key={`pc-${i}`}>{item}</li>)}</ul>
                </div>
              </div>
            )}

            {/* Key Information grid */}
            <div className="detail-section">
              <h3>Record Information</h3>
              <div className="info-grid">
                <div className="info-item">
                  <span className="info-label">Record ID</span>
                  <span className="info-value code">{detail.record_id}</span>
                </div>
                <div className="info-item">
                  <span className="info-label">Record Type</span>
                  <span className="info-value">{detail.record_type || '—'}</span>
                </div>
                <div className="info-item">
                  <span className="info-label">Severity</span>
                  <span className="info-value">
                    <span className={`severity-badge ${getSevClass(detail.severity)}`}>{detail.severity}</span>
                  </span>
                </div>
                <div className="info-item">
                  <span className="info-label">Priority</span>
                  <span className="info-value">{detail.priority || '—'}</span>
                </div>
                <div className="info-item">
                  <span className="info-label">Anomaly Type</span>
                  <span className="info-value">{detail.anomaly_type || '—'}</span>
                </div>
                <div className="info-item">
                  <span className="info-label">Confidence</span>
                  <span className="info-value">
                    {detail.confidence ? `${(detail.confidence * 100).toFixed(0)}%` : '—'}
                  </span>
                </div>
              </div>
            </div>

          </div>
        )}

        {/* ── Footer ───────────────────────────────────────── */}
        <div className="detail-footer">
          <button className="close-footer-button" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  )
}
