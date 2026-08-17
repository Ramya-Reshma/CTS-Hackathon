import React, { useState, useEffect } from 'react'
import { useMedlyticsData } from '../../hooks/useMedlyticsData'
import { getAnomalyDetail } from '../../services/api'
import { fmtLabel, fmtNum, fmtBool } from '../../utils/statusUtils'
import Filters from '../Filters'
import './shared-pages.css'

export default function AnomalyPage() {
  const { anomalies, statistics, isLoading, error } = useMedlyticsData()
  const [selectedId, setSelectedId] = useState(null)
  const [selectedRecord, setSelectedRecord] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [sevFilter, setSevFilter] = useState(null)

  // Auto-select first anomaly when list is loaded
  useEffect(() => {
    if (anomalies.length > 0 && !selectedId) {
      setSelectedId(anomalies[0].id)
    }
  }, [anomalies, selectedId])

  // Load detailed record whenever selectedId changes
  useEffect(() => {
    if (!selectedId) return
    setDetailLoading(true)
    getAnomalyDetail(selectedId)
      .then(data => setSelectedRecord(data))
      .catch(err => console.error('Failed to load anomaly detail:', err))
      .finally(() => setDetailLoading(false))
  }, [selectedId])

  if (isLoading) {
    return (
      <div className="loading-container">
        <div className="spinner" />
        <p className="loading-text">Loading Anomaly Detection Data...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="error-banner" role="alert">
        <span>Unable to load anomaly data. Please check backend connection.</span>
      </div>
    )
  }

  const filtered = anomalies.filter(a => {
    const matchesSev = !sevFilter || a.severity === sevFilter
    const matchesSearch = !searchTerm ||
      (a.record_id && a.record_id.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (a.record_type && a.record_type.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (a.anomaly_type && a.anomaly_type.toLowerCase().includes(searchTerm.toLowerCase()))
    return matchesSev && matchesSearch
  })

  const full = selectedRecord?.full_record || {}
  const signals = selectedRecord?.anomaly_signals || {}

  return (
    <div className="ml-page">
      <div className="ml-page-heading">
        <h1>Anomaly Detection</h1>
        <p>ML-based identification of unusual claim behavior across multiple statistical and isolation models.</p>
      </div>

      {/* Record Selector and Details Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: '20px' }}>
        
        {/* Left: Record List Selector */}
        <div className="ml-info-card" style={{ height: 'fit-content' }}>
          <div className="ml-info-card-header">
            <div className="ml-info-card-title">
              <h2>Monitored Records</h2>
              <p>Select a record to inspect anomaly signals</p>
            </div>
          </div>
          <div style={{ padding: '12px' }}>
            <input
              type="text"
              placeholder="Search records..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              style={{ width: '100%', marginBottom: '8px' }}
            />
            <div style={{ display: 'flex', gap: '4px', marginBottom: '12px' }}>
              <button
                className={`filter-button ${!sevFilter ? 'active' : ''}`}
                style={{ flex: 1, padding: '4px 6px', fontSize: '11px' }}
                onClick={() => setSevFilter(null)}
              >
                All
              </button>
              <button
                className={`filter-button high ${sevFilter === 'HIGH' ? 'active' : ''}`}
                style={{ flex: 1, padding: '4px 6px', fontSize: '11px' }}
                onClick={() => setSevFilter('HIGH')}
              >
                High
              </button>
              <button
                className={`filter-button medium ${sevFilter === 'MEDIUM' ? 'active' : ''}`}
                style={{ flex: 1, padding: '4px 6px', fontSize: '11px' }}
                onClick={() => setSevFilter('MEDIUM')}
              >
                Med
              </button>
              <button
                className={`filter-button low ${sevFilter === 'LOW' ? 'active' : ''}`}
                style={{ flex: 1, padding: '4px 6px', fontSize: '11px' }}
                onClick={() => setSevFilter('LOW')}
              >
                Low
              </button>
            </div>
          </div>
          <div style={{ maxHeight: '520px', overflowY: 'auto' }}>
            {filtered.length === 0 ? (
              <div className="ml-empty">No records matching filter</div>
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
                  <span className={`severity-badge severity-${(item.severity || '').toLowerCase()}`}>
                    {item.severity}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right: Selected Anomaly Details */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {detailLoading ? (
            <div className="loading-container">
              <div className="spinner" />
              <p className="loading-text">Loading record signals...</p>
            </div>
          ) : selectedRecord ? (
            <>
              {/* Record Identification Bar */}
              <div style={{ background: 'var(--surface-card)', border: '1px solid var(--border-light)', borderRadius: 'var(--radius-md)', padding: '14px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--gray-400)', fontWeight: 600, letterSpacing: '0.8px' }}>
                    Record Identification
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '4px' }}>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '18px', fontWeight: 700, color: 'var(--navy-900)' }}>
                      {selectedRecord.record_id}
                    </span>
                    <span className="type-badge">{fmtLabel(selectedRecord.record_type)}</span>
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '12px', color: 'var(--gray-500)' }}>Status:</span>
                  <span className={`ml-status-badge ${full.ML_Is_Anomalous || full.ISO_Is_Anomaly ? 'ml-status-anomalous' : 'ml-status-normal'}`}>
                    {full.ML_Is_Anomalous || full.ISO_Is_Anomaly ? 'ANOMALOUS' : 'NORMAL'}
                  </span>
                </div>
              </div>

              {/* Anomaly Detection Information Card */}
              <div className="ml-info-card">
                <div className="ml-info-card-header">
                  <div className="ml-info-card-title">
                    <h2>Anomaly Detection Information</h2>
                    <p>Statistical and machine learning anomaly indicators</p>
                  </div>
                  <span className={`ml-status-badge ${full.ML_Is_Anomalous || full.ISO_Is_Anomaly ? 'ml-status-anomalous' : 'ml-status-normal'}`}>
                    {full.ML_Is_Anomalous || full.ISO_Is_Anomaly ? 'ANOMALOUS' : 'NORMAL'}
                  </span>
                </div>
                <div className="ml-field-grid">
                  <div className="ml-field-row">
                    <span className="ml-field-label">Detection Model</span>
                    <span className="ml-field-value">Isolation Forest + Robust Statistics</span>
                  </div>
                  <div className="ml-field-row">
                    <span className="ml-field-label">Anomaly Type</span>
                    <span className="ml-field-value">{selectedRecord.anomaly_type || 'ML Multivariate'}</span>
                  </div>
                  <div className="ml-field-row">
                    <span className="ml-field-label">Raw Score</span>
                    <span className="ml-field-value mono">
                      {full.ISO_Raw_Score != null ? fmtNum(full.ISO_Raw_Score, 4) : 'Not available'}
                    </span>
                  </div>
                  <div className="ml-field-row">
                    <span className="ml-field-label">Severity</span>
                    <span className="ml-field-value">
                      {full.ISO_Severity_0to1 != null ? fmtNum(full.ISO_Severity_0to1, 2) : (selectedRecord.severity || 'Not available')}
                    </span>
                  </div>
                  <div className="ml-field-row">
                    <span className="ml-field-label">Correlation Anomaly</span>
                    <span className={`ml-field-value ${full.Correlation_Anomaly ? 'ml-bool-yes' : 'ml-bool-no'}`}>
                      {full.Correlation_Anomaly != null ? (full.Correlation_Anomaly ? 'Flagged' : 'Normal') : 'Normal'}
                    </span>
                  </div>
                  <div className="ml-field-row">
                    <span className="ml-field-label">Correlation Residual</span>
                    <span className="ml-field-value mono">
                      {full.Correlation_Residual != null ? fmtNum(full.Correlation_Residual, 4) : 'Not available'}
                    </span>
                  </div>
                  <div className="ml-field-row">
                    <span className="ml-field-label">Quantity / Supply Anomaly</span>
                    <span className={`ml-field-value ${full.Quantity_Supply_Anomaly ? 'ml-bool-yes' : 'ml-bool-no'}`}>
                      {full.Quantity_Supply_Anomaly != null ? (full.Quantity_Supply_Anomaly ? 'Flagged' : 'Normal') : 'Normal'}
                    </span>
                  </div>
                  <div className="ml-field-row">
                    <span className="ml-field-label">ML Signals Count</span>
                    <span className="ml-field-value">
                      {full.ML_Anomaly_Signal_Count != null ? full.ML_Anomaly_Signal_Count : 1}
                    </span>
                  </div>
                </div>
              </div>

              {/* Detection Signals */}
              <div className="ml-info-card">
                <div className="ml-info-card-header">
                  <div className="ml-info-card-title">
                    <h2>Detection Signals</h2>
                    <p>Evidence identified by detection pipeline</p>
                  </div>
                </div>
                <div className="ml-info-card-body">
                  <div className="ml-signals-list">
                    {full.ISO_Is_Anomaly && (
                      <div className="ml-signal-item">
                        <span className="ml-signal-dot" />
                        <div>Isolation Forest identified an unusual multivariate distribution pattern (Score: {fmtNum(full.ISO_Raw_Score, 4)})</div>
                      </div>
                    )}
                    {full.Correlation_Anomaly && (
                      <div className="ml-signal-item">
                        <span className="ml-signal-dot" />
                        <div>Correlation breakdown between Paid Amount and Allowed Amount (Residual: {fmtNum(full.Correlation_Residual, 4)})</div>
                      </div>
                    )}
                    {full.Quantity_Supply_Anomaly && (
                      <div className="ml-signal-item">
                        <span className="ml-signal-dot" />
                        <div>Quantity Dispensed vs Days Supply discrepancy detected (Residual: {fmtNum(full.Quantity_Supply_Residual, 4)})</div>
                      </div>
                    )}
                    {selectedRecord.primary_signal && (
                      <div className="ml-signal-item">
                        <span className="ml-signal-dot" />
                        <div><strong>Primary Signal:</strong> {selectedRecord.primary_signal}</div>
                      </div>
                    )}
                    {selectedRecord.likely_root_cause && (
                      <div className="ml-signal-item">
                        <span className="ml-signal-dot" />
                        <div><strong>Likely Cause:</strong> {selectedRecord.likely_root_cause}</div>
                      </div>
                    )}
                    {!full.ISO_Is_Anomaly && !full.Correlation_Anomaly && !full.Quantity_Supply_Anomaly && !selectedRecord.primary_signal && (
                      <div className="ml-empty">No active anomaly triggers on this record.</div>
                    )}
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="ml-empty">Select a record from the left to view details.</div>
          )}
        </div>

      </div>
    </div>
  )
}
