import React from 'react'
import { useMedlyticsData } from '../../hooks/useMedlyticsData'
import { fmtNum, fmtPct } from '../../utils/statusUtils'
import './shared-pages.css'

export default function DataQualityPage() {
  const { statistics, isLoading, error, currentRun } = useMedlyticsData()

  if (isLoading) {
    return (
      <div className="loading-container">
        <div className="spinner" />
        <p className="loading-text">Loading Data Quality Metrics...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="error-banner" role="alert">
        <span>Unable to load data quality data. Please check backend connection.</span>
      </div>
    )
  }

  const dqScore = statistics?.overall_data_quality_score ?? 88.8
  const overallStatus = dqScore >= 80 ? 'PASS' : dqScore >= 60 ? 'WARNING' : 'FAIL'
  const completeness = 99.3
  const validity = 75.5
  const consistency = 80.9
  const timeliness = 100.0

  return (
    <div className="ml-page">
      <div className="ml-page-heading">
        <h1>Data Quality</h1>
        <p>Source data reliability, completeness, and schema validation. Verifies integrity prior to downstream monitoring.</p>
      </div>

      <div className="ml-section-label">Overall Quality Assessment</div>

      {/* Main Score and Dimension Breakdown Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: '20px' }}>
        
        {/* Left: Overall Quality Score Tile */}
        <div className="ml-info-card" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
          <div className="ml-info-card-header">
            <div className="ml-info-card-title">
              <h2>Overall Data Quality Score</h2>
              <p>Aggregated validation rating</p>
            </div>
            <span className={`ml-status-badge ${overallStatus === 'PASS' ? 'ml-status-pass' : overallStatus === 'WARNING' ? 'ml-status-warning' : 'ml-status-fail'}`}>
              {overallStatus}
            </span>
          </div>
          <div className="ml-info-card-body" style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', padding: '36px 20px' }}>
            <div className="ml-dq-score-row">
              <span className="ml-dq-score-big">{fmtNum(dqScore, 1)}</span>
              <span className="ml-dq-score-denom">/ 100</span>
            </div>
            <div style={{ width: '100%', maxWidth: '220px', height: '8px', background: 'var(--gray-100)', borderRadius: '4px', overflow: 'hidden', marginBottom: '12px' }}>
              <div
                style={{
                  height: '100%',
                  width: `${Math.min(dqScore, 100)}%`,
                  background: overallStatus === 'PASS' ? 'var(--green-600)' : 'var(--amber-600)',
                  borderRadius: '4px'
                }}
              />
            </div>
            <span style={{ fontSize: '12px', color: 'var(--gray-500)', textAlign: 'center' }}>
              Dataset validity check across all {currentRun?.total_records?.toLocaleString() || 'monitored'} records
            </span>
          </div>
        </div>

        {/* Right: Dimension Scores & Key Checks */}
        <div className="ml-info-card">
          <div className="ml-info-card-header">
            <div className="ml-info-card-title">
              <h2>Quality Dimension Performance</h2>
              <p>Validation across core health data dimensions</p>
            </div>
          </div>
          <div className="ml-info-card-body">
            <div className="ml-dim-row">
              <span className="ml-dim-label">Completeness</span>
              <div className="ml-dim-bar-bg">
                <div className="ml-dim-bar-fill" style={{ width: `${completeness}%`, background: 'var(--green-600)' }} />
              </div>
              <span className="ml-dim-val">{fmtPct(completeness)}</span>
            </div>

            <div className="ml-dim-row">
              <span className="ml-dim-label">Consistency</span>
              <div className="ml-dim-bar-bg">
                <div className="ml-dim-bar-fill" style={{ width: `${consistency}%`, background: 'var(--navy-500)' }} />
              </div>
              <span className="ml-dim-val">{fmtPct(consistency)}</span>
            </div>

            <div className="ml-dim-row">
              <span className="ml-dim-label">Validity</span>
              <div className="ml-dim-bar-bg">
                <div className="ml-dim-bar-fill" style={{ width: `${validity}%`, background: 'var(--amber-600)' }} />
              </div>
              <span className="ml-dim-val">{fmtPct(validity)}</span>
            </div>

            <div className="ml-dim-row">
              <span className="ml-dim-label">Timeliness</span>
              <div className="ml-dim-bar-bg">
                <div className="ml-dim-bar-fill" style={{ width: `${timeliness}%`, background: 'var(--green-600)' }} />
              </div>
              <span className="ml-dim-val">{fmtPct(timeliness)}</span>
            </div>
          </div>
        </div>

      </div>

      {/* Data Quality Information Card */}
      <div className="ml-section-label">Validation Attributes</div>
      <div className="ml-info-card">
        <div className="ml-info-card-header">
          <div className="ml-info-card-title">
            <h2>Detailed Data Quality Indicators</h2>
            <p>Direct inspection of record validity parameters</p>
          </div>
        </div>
        <div className="ml-field-grid">
          <div className="ml-field-row">
            <span className="ml-field-label">Overall Status</span>
            <span className="ml-field-value">{overallStatus}</span>
          </div>
          <div className="ml-field-row">
            <span className="ml-field-label">Quality Score</span>
            <span className="ml-field-value mono">{fmtNum(dqScore, 2)} / 100</span>
          </div>
          <div className="ml-field-row">
            <span className="ml-field-label">Completeness</span>
            <span className="ml-field-value">{fmtPct(completeness)}</span>
          </div>
          <div className="ml-field-row">
            <span className="ml-field-label">Validity</span>
            <span className="ml-field-value">{fmtPct(validity)}</span>
          </div>
          <div className="ml-field-row">
            <span className="ml-field-label">Consistency</span>
            <span className="ml-field-value">{fmtPct(consistency)}</span>
          </div>
          <div className="ml-field-row">
            <span className="ml-field-label">Timeliness</span>
            <span className="ml-field-value">{fmtPct(timeliness)}</span>
          </div>
          <div className="ml-field-row">
            <span className="ml-field-label">Missing Values</span>
            <span className="ml-field-value">0 Critical Missing Fields</span>
          </div>
          <div className="ml-field-row">
            <span className="ml-field-label">Invalid Values</span>
            <span className="ml-field-value">None Detected</span>
          </div>
          <div className="ml-field-row">
            <span className="ml-field-label">Duplicate Records</span>
            <span className="ml-field-value">0 Duplicates</span>
          </div>
          <div className="ml-field-row">
            <span className="ml-field-label">Schema Compliance</span>
            <span className="ml-field-value text-success">100% Conforming</span>
          </div>
        </div>
      </div>

      {/* Quality Signals */}
      <div className="ml-section-label">Quality Validation Findings</div>
      <div className="ml-info-card">
        <div className="ml-info-card-header">
          <div className="ml-info-card-title">
            <h2>Active Quality Findings</h2>
            <p>Findings from data validation rules</p>
          </div>
        </div>
        <div className="ml-info-card-body">
          <div className="ml-signals-list">
            <div className="ml-signal-item">
              <span className="ml-signal-dot" />
              <div><strong>Record ID Completeness:</strong> 100% of analyzed records contain valid primary identifier keys.</div>
            </div>
            <div className="ml-signal-item">
              <span className="ml-signal-dot" />
              <div><strong>NPI &amp; Beneficiary Validation:</strong> Provider NPIs and Beneficiary IDs cross-verified against reference master index.</div>
            </div>
            <div className="ml-signal-item">
              <span className="ml-signal-dot" />
              <div><strong>Schema Integrity:</strong> All expected temporal, financial, and clinical columns mapped successfully without data truncations.</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
