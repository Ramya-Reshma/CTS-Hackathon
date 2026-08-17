import React, { useState, useEffect } from 'react'
import { useMedlyticsData } from '../../hooks/useMedlyticsData'
import { getAnomalyDetail } from '../../services/api'
import { fmtLabel, fmtNum, fmtPct } from '../../utils/statusUtils'
import './shared-pages.css'

export default function RecommendationPage() {
  const { anomalies, statistics, isLoading, error } = useMedlyticsData()
  const [selectedId, setSelectedId] = useState(null)
  const [selectedRecord, setSelectedRecord] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [showMonitoringDetails, setShowMonitoringDetails] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [recommendationLoaded, setRecommendationLoaded] = useState(false)

  // Auto-select first record on mount
  useEffect(() => {
    if (anomalies.length > 0 && !selectedId) {
      setSelectedId(anomalies[0].id)
    }
  }, [anomalies, selectedId])

  // Fetch detail for selected record
  useEffect(() => {
    if (!selectedId) return
    setDetailLoading(true)
    setRecommendationLoaded(false)
    getAnomalyDetail(selectedId)
      .then(data => {
        setSelectedRecord(data)
        setRecommendationLoaded(true)
      })
      .catch(err => console.error('Failed to load recommendation context:', err))
      .finally(() => setDetailLoading(false))
  }, [selectedId])

  const handleGenerate = () => {
    if (!selectedId) return
    setIsGenerating(true)
    // Simulate generation / refresh from backend recommendation pipeline
    setTimeout(() => {
      getAnomalyDetail(selectedId)
        .then(data => {
          setSelectedRecord(data)
          setRecommendationLoaded(true)
        })
        .finally(() => setIsGenerating(false))
    }, 600)
  }

  if (isLoading) {
    return (
      <div className="loading-container">
        <div className="spinner" />
        <p className="loading-text">Loading Recommendation Engine...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="error-banner" role="alert">
        <span>Unable to load records for recommendation. Please check backend connection.</span>
      </div>
    )
  }

  const full = selectedRecord?.full_record || {}
  const anomalySignals = selectedRecord?.anomaly_signals || {}
  
  // Monitoring 3-pillar context for selected record
  const isAnomalous = full.ML_Is_Anomalous === true || full.ISO_Is_Anomaly === true || selectedRecord?.severity === 'HIGH' || selectedRecord?.severity === 'MEDIUM'
  const slaStatus = full.SLA_Status ?? full.status ?? 'ON TRACK'
  const dqStatus = (statistics?.overall_data_quality_score ?? 88.8) >= 80 ? 'PASS' : 'WARNING'

  const filtered = anomalies.filter(a => {
    return !searchTerm || (a.record_id && a.record_id.toLowerCase().includes(searchTerm.toLowerCase()))
  })

  // Evidence list from backend
  const evidenceList = Array.isArray(selectedRecord?.evidence) && selectedRecord.evidence.length > 0
    ? selectedRecord.evidence
    : selectedRecord?.primary_signal
      ? [selectedRecord.primary_signal]
      : []

  const observedFacts = Array.isArray(selectedRecord?.observed_facts) ? selectedRecord.observed_facts : []
  const possibleCauses = Array.isArray(selectedRecord?.possible_causes) ? selectedRecord.possible_causes : []

  return (
    <div className="ml-page">
      {/* Header */}
      <div className="ml-page-heading">
        <h1>Recommendation Engine</h1>
        <p>Evidence-grounded operational recommendations. Combines monitoring signals with retrieved evidence to generate an explainable recommendation.</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: '20px' }}>
        
        {/* Left: Record Selector */}
        <div className="ml-info-card" style={{ height: 'fit-content' }}>
          <div className="ml-info-card-header">
            <div className="ml-info-card-title">
              <h2>Select Record</h2>
              <p>Choose record to analyze</p>
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
          <div style={{ maxHeight: '520px', overflowY: 'auto' }}>
            {filtered.length === 0 ? (
              <div className="ml-empty">No records found</div>
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

        {/* Right: Recommendation & Evidence Content */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          {detailLoading ? (
            <div className="loading-container">
              <div className="spinner" />
              <p className="loading-text">Loading record analysis context...</p>
            </div>
          ) : selectedRecord ? (
            <>
              {/* 1. RECORD UNDER ANALYSIS */}
              <div style={{ background: 'var(--surface-card)', border: '1px solid var(--border-light)', borderRadius: 'var(--radius-md)', padding: '16px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--gray-400)', fontWeight: 600, letterSpacing: '0.8px' }}>
                    Record Under Analysis
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '4px' }}>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '20px', fontWeight: 700, color: 'var(--navy-900)' }}>
                      {selectedRecord.record_id}
                    </span>
                    <span className="type-badge">{fmtLabel(selectedRecord.record_type)}</span>
                    <span className={`priority-badge priority-${(selectedRecord.priority || '').toLowerCase().replace(/\s+/g, '-')}`}>
                      {selectedRecord.priority || 'Priority-3'}
                    </span>
                  </div>
                </div>

                <button
                  className="analyze-button"
                  onClick={handleGenerate}
                  disabled={isGenerating}
                  style={{ padding: '8px 18px', fontSize: '13px' }}
                >
                  {isGenerating ? (
                    <><span className="spinner-small" /> Analyzing...</>
                  ) : (
                    'Generate Recommendation'
                  )}
                </button>
              </div>

              {/* 2. MONITORING CONTEXT (3 PILLARS) */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <div style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--gray-400)', fontWeight: 600, letterSpacing: '0.8px' }}>
                    Monitoring Context
                  </div>
                  <button
                    onClick={() => setShowMonitoringDetails(o => !o)}
                    style={{ background: 'none', border: 'none', color: 'var(--navy-500)', fontSize: '12px', cursor: 'pointer', padding: 0 }}
                  >
                    {showMonitoringDetails ? '▲ Hide Details' : '▼ View Monitoring Details'}
                  </button>
                </div>

                <div className="ml-summary-trio">
                  <div className="ml-summary-card anomaly" style={{ padding: '12px 16px' }}>
                    <span className="ml-summary-card-label">Anomaly Status</span>
                    <div style={{ marginTop: '4px' }}>
                      <span className={`ml-status-badge ${isAnomalous ? 'ml-status-anomalous' : 'ml-status-normal'}`}>
                        {isAnomalous ? 'ANOMALOUS' : 'NORMAL'}
                      </span>
                    </div>
                  </div>

                  <div className="ml-summary-card sla" style={{ padding: '12px 16px' }}>
                    <span className="ml-summary-card-label">SLA Risk</span>
                    <div style={{ marginTop: '4px' }}>
                      <span className={`ml-status-badge ${slaStatus === 'BREACHED' ? 'ml-status-breached' : slaStatus === 'AT_RISK' ? 'ml-status-at-risk' : 'ml-status-on-track'}`}>
                        {slaStatus}
                      </span>
                    </div>
                  </div>

                  <div className="ml-summary-card quality" style={{ padding: '12px 16px' }}>
                    <span className="ml-summary-card-label">Data Quality</span>
                    <div style={{ marginTop: '4px' }}>
                      <span className={`ml-status-badge ${dqStatus === 'PASS' ? 'ml-status-pass' : 'ml-status-warning'}`}>
                        {dqStatus}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Expandable Monitoring Details */}
                {showMonitoringDetails && (
                  <div className="ml-info-card" style={{ marginTop: '10px' }}>
                    <div className="ml-field-grid">
                      <div className="ml-field-row">
                        <span className="ml-field-label">Anomaly Model</span>
                        <span className="ml-field-value">Isolation Forest + Correlation</span>
                      </div>
                      <div className="ml-field-row">
                        <span className="ml-field-label">Primary Anomaly Signal</span>
                        <span className="ml-field-value">{selectedRecord.primary_signal || 'No anomalous signal'}</span>
                      </div>
                      <div className="ml-field-row">
                        <span className="ml-field-label">SLA Target</span>
                        <span className="ml-field-value">{full.sla_target_days ? `${full.sla_target_days} Days` : '2.0 Days'}</span>
                      </div>
                      <div className="ml-field-row">
                        <span className="ml-field-label">SLA Breach Risk</span>
                        <span className="ml-field-value">{full.Breach_Risk || 'Low Exposure'}</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* 3. AI RECOMMENDATION (MAIN FOCAL CARD) */}
              <div className="ml-info-card" style={{ borderLeft: '4px solid var(--navy-600)' }}>
                <div className="ml-info-card-header" style={{ background: 'var(--navy-50)' }}>
                  <div className="ml-info-card-title">
                    <h2 style={{ color: 'var(--navy-900)' }}>AI Operational Recommendation</h2>
                    <p>Evidence-grounded action determined by healthcare intelligence pipeline</p>
                  </div>
                  {selectedRecord.confidence != null && (
                    <span style={{ fontSize: '11px', fontWeight: 600, background: 'var(--surface-card)', padding: '3px 8px', borderRadius: '4px', border: '1px solid var(--border-light)', color: 'var(--gray-700)' }}>
                      Confidence: {(selectedRecord.confidence * 100).toFixed(0)}%
                    </span>
                  )}
                </div>
                <div className="ml-info-card-body" style={{ padding: '20px 24px' }}>
                  <div style={{ fontSize: '15px', fontWeight: 600, color: 'var(--navy-900)', lineHeight: '1.6', marginBottom: '14px' }}>
                    {selectedRecord.recommended_action || (
                      isAnomalous
                        ? 'Initiate secondary clinical audit on authorization link and verify provider billing frequency.'
                        : 'Routine adjudication approved. No operational hold required.'
                    )}
                  </div>

                  {selectedRecord.impact && (
                    <div style={{ background: 'var(--surface-inset)', border: '1px solid var(--border-light)', borderRadius: 'var(--radius-sm)', padding: '12px 16px', marginTop: '12px' }}>
                      <div style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--gray-400)', fontWeight: 600, letterSpacing: '0.6px', marginBottom: '4px' }}>
                        Operational Impact
                      </div>
                      <div style={{ fontSize: '13px', color: 'var(--gray-700)' }}>
                        {selectedRecord.impact}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* 4. RECOMMENDATION RATIONALE ("Why this recommendation?") */}
              <div className="ml-info-card">
                <div className="ml-info-card-header">
                  <div className="ml-info-card-title">
                    <h2>Why this recommendation?</h2>
                    <p>Explainable rationale derived from monitoring signals and evidence</p>
                  </div>
                </div>
                <div className="ml-info-card-body">
                  <div style={{ fontSize: '13px', color: 'var(--gray-700)', lineHeight: '1.6', marginBottom: '16px' }}>
                    {selectedRecord.likely_root_cause || (
                      isAnomalous
                        ? 'The claim exhibits statistical divergence from standard peer provider billing profiles. Multidimensional feature evaluation identified irregular volume velocity and billing ratio.'
                        : 'All metrics fall within normal operational baselines and standard service level agreement deadlines.'
                    )}
                  </div>

                  {/* Observed facts / Hypotheses if present */}
                  {observedFacts.length > 0 && (
                    <div style={{ marginTop: '12px' }}>
                      <div style={{ fontSize: '11px', fontWeight: 600, textTransform: 'uppercase', color: 'var(--gray-400)', marginBottom: '6px' }}>
                        Observed Facts
                      </div>
                      <ul style={{ paddingLeft: '18px', fontSize: '13px', color: 'var(--gray-700)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        {observedFacts.map((fact, idx) => (
                          <li key={idx}>{fact}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {selectedRecord.additional_checks && (
                    <div style={{ marginTop: '14px', padding: '10px 14px', background: 'var(--amber-50)', border: '1px solid var(--amber-100)', borderRadius: 'var(--radius-sm)' }}>
                      <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--amber-700)', marginBottom: '2px' }}>
                        Additional Verification Recommended
                      </div>
                      <div style={{ fontSize: '12px', color: 'var(--gray-700)' }}>
                        {selectedRecord.additional_checks}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* 5. EVIDENCE RETRIEVED (RAG GROUNDING) */}
              <div className="ml-info-card">
                <div className="ml-info-card-header">
                  <div className="ml-info-card-title">
                    <h2>Evidence Retrieved</h2>
                    <p>Relevant knowledge base &amp; policy evidence retrieved by the RAG pipeline</p>
                  </div>
                </div>
                <div className="ml-info-card-body">
                  {evidenceList.length === 0 ? (
                    <div className="ml-empty">
                      No policy evidence citations attached to this record.
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      {evidenceList.map((evText, i) => (
                        <div
                          key={i}
                          style={{
                            background: 'var(--surface-inset)',
                            border: '1px solid var(--border-light)',
                            borderRadius: 'var(--radius-sm)',
                            padding: '14px 16px'
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                            <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--navy-800)', letterSpacing: '0.5px' }}>
                              EVIDENCE 0{i + 1}
                            </span>
                            <span style={{ fontSize: '10px', textTransform: 'uppercase', background: 'var(--navy-100)', color: 'var(--navy-700)', padding: '2px 8px', borderRadius: '4px', fontWeight: 600 }}>
                              Retrieved Policy / Finding
                            </span>
                          </div>
                          <div style={{ fontSize: '13px', color: 'var(--gray-700)', lineHeight: '1.5' }}>
                            {evText}
                          </div>
                          <div style={{ fontSize: '11px', color: 'var(--gray-400)', marginTop: '8px', borderTop: '1px solid var(--gray-100)', paddingTop: '6px' }}>
                            Source: Historical Knowledge Base &amp; Adjudication Guidelines
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* 6. SUPPORTING SIGNALS */}
              <div className="ml-info-card">
                <div className="ml-info-card-header">
                  <div className="ml-info-card-title">
                    <h2>Supporting Monitoring Signals</h2>
                    <p>Active telemetry across Anomaly, SLA, and Quality engines</p>
                  </div>
                </div>
                <div className="ml-info-card-body">
                  <div className="ml-signals-list">
                    <div className="ml-signal-item">
                      <span className="ml-signal-dot" />
                      <div>
                        <strong>Anomaly Engine:</strong> {selectedRecord.anomaly_type || 'ML Multivariate'} (Severity: {selectedRecord.severity || 'Normal'})
                      </div>
                    </div>
                    <div className="ml-signal-item">
                      <span className="ml-signal-dot" />
                      <div>
                        <strong>SLA Engine:</strong> Status: {slaStatus} · Target: {full.sla_target_days ? `${full.sla_target_days} Days` : '2.0 Days'} · Risk Level: {full.Risk_Level || selectedRecord.severity || 'Low'}
                      </div>
                    </div>
                    <div className="ml-signal-item">
                      <span className="ml-signal-dot" />
                      <div>
                        <strong>Data Quality Engine:</strong> Schema &amp; Identifier Validation Status: {dqStatus} (Overall Score: {fmtNum(statistics?.overall_data_quality_score ?? 88.8, 1)} / 100)
                      </div>
                    </div>
                  </div>
                </div>
              </div>

            </>
          ) : (
            <div className="ml-empty">
              Select a record to generate an evidence-grounded recommendation.
            </div>
          )}
        </div>

      </div>
    </div>
  )
}
