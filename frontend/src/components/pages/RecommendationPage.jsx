import React, { useState, useEffect, useRef } from 'react'
import { useMedlyticsData } from '../../hooks/useMedlyticsData'
import {
  getAnomalyDetail,
  evaluateAutoResolution,
  executeAutoResolution,
  getAutoResolutionHistory,
} from '../../services/api'
import { fmtLabel, fmtNum } from '../../utils/statusUtils'
import './shared-pages.css'

/* ─── Helper constants ─── */
const EVIDENCE_AUTHORITY_LABELS = {
  SOURCE: { label: 'L1 · Source Data', color: '#16a34a', bg: '#f0fdf4' },
  BACKEND: { label: 'L2 · Backend Engine', color: '#2563eb', bg: '#eff6ff' },
  VALIDATION: { label: 'L3 · Validation', color: '#7c3aed', bg: '#f5f3ff' },
  RAG: { label: 'L4 · RAG Knowledge', color: '#d97706', bg: '#fffbeb' },
  LLM: { label: 'L5 · LLM Reasoning', color: '#6b7280', bg: '#f9fafb' },
}

function decisionBadge(state) {
  if (state === 'AUTO_FIX_ELIGIBLE') return { icon: '✓', label: 'SAFE TO AUTO-FIX', cls: 'ares-badge-safe' }
  if (state === 'MANUAL_REVIEW_REQUIRED') return { icon: '⚠', label: 'MANUAL REVIEW REQUIRED', cls: 'ares-badge-warn' }
  if (state === 'NO_ACTION_REQUIRED') return { icon: '✓', label: 'NO ACTION REQUIRED', cls: 'ares-badge-none' }
  return { icon: '·', label: state || '—', cls: 'ares-badge-warn' }
}

function statusBadge(status) {
  if (status === 'AUTO_FIXED') return { icon: '✓', label: 'AUTO FIXED', cls: 'ares-result-success' }
  if (status === 'FIX_FAILED_ROLLED_BACK') return { icon: '↩', label: 'ROLLED BACK', cls: 'ares-result-rollback' }
  if (status === 'NO_ACTION_REQUIRED') return { icon: '✓', label: 'NO ACTION', cls: 'ares-result-none' }
  if (status === 'MANUAL_REVIEW_REQUIRED') return { icon: '⚠', label: 'MANUAL REVIEW', cls: 'ares-result-warn' }
  return { icon: '·', label: status || '—', cls: 'ares-result-warn' }
}

/* ─── Auto-Resolution Panel ─── */
function AutoResolutionPanel({ selectedRecord, runId }) {
  const [evaluation, setEvaluation] = useState(null)
  const [evalLoading, setEvalLoading] = useState(false)
  const [execLoading, setExecLoading] = useState(false)
  const [execResult, setExecResult] = useState(null)
  const [history, setHistory] = useState([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const [showEvidence, setShowEvidence] = useState(false)
  const [error, setError] = useState(null)

  const full = selectedRecord?.full_record || {}
  const anomalySignals = selectedRecord?.anomaly_signals || {}

  /* Keep a stable ref to the selected record to avoid useCallback dependency churn */
  const selectedRecordRef = useRef(selectedRecord)
  selectedRecordRef.current = selectedRecord

  /* Evaluate on record change — keyed ONLY on record_id to prevent infinite loops */
  useEffect(() => {
    if (!selectedRecord?.record_id) return
    setEvaluation(null)
    setExecResult(null)
    setConfirmOpen(false)
    setError(null)

    // Build payload inline using current ref value (stable across re-renders)
    const rec = selectedRecordRef.current
    const fr = rec?.full_record || {}
    const sigs = rec?.anomaly_signals || {}

    const evidenceList = []
    if (rec?.record_id) evidenceList.push({ source: 'SOURCE_RECORD', field: 'Record_ID', value: rec.record_id, authority: 'SOURCE' })
    if (fr.Billed_Amount !== undefined) evidenceList.push({ source: 'SOURCE_RECORD', field: 'Billed_Amount', value: fr.Billed_Amount, authority: 'SOURCE' })
    if (fr.Allowed_Amount !== undefined) evidenceList.push({ source: 'SOURCE_RECORD', field: 'Allowed_Amount', value: fr.Allowed_Amount, authority: 'SOURCE' })
    if (fr.SLA_Status !== undefined) evidenceList.push({ source: 'SLA_ENGINE', field: 'SLA_Status', value: fr.SLA_Status, authority: 'BACKEND' })
    if (sigs.iso_score !== undefined) evidenceList.push({ source: 'ISOLATION_FOREST', field: 'ISO_Score', value: sigs.iso_score, authority: 'BACKEND' })
    if (Array.isArray(rec?.evidence)) rec.evidence.forEach(ev => evidenceList.push({ source: 'RAG_KB', field: 'Policy_Finding', value: ev, authority: 'RAG' }))
    if (rec?.likely_root_cause) evidenceList.push({ source: 'RCA_AGENT', field: 'Root_Cause', value: rec.likely_root_cause, authority: 'LLM' })

    // 1. Cross-Layer Detector Signals (Preserve canonical multi-layer backend findings)
    const isAnomalous = fr.ML_Is_Anomalous === true || fr.ISO_Is_Anomaly === true || fr.Stat_Zscore_Anomaly === true || fr.Stat_IQR_Anomaly === true || (rec?.anomaly_type && rec.anomaly_type !== 'Normal')
    const isCorrelation = fr.Correlation_Anomaly === true || (rec?.anomaly_type && rec.anomaly_type.toLowerCase().includes('correlation')) || (sigs?.correlation_residual && Math.abs(sigs.correlation_residual) > 3.0)
    const isQuantitySupply = fr.Quantity_Supply_Anomaly === true || (rec?.anomaly_type && rec.anomaly_type.toLowerCase().includes('quantity'))
    const isSlaBreached = fr.SLA_Status === 'BREACHED' || fr.SLA_Breached === true
    const isSlaMissingOutput = isSlaBreached && !fr.SLA_Status
    const isMissingRequiredSource = !fr.Provider_NPI || !fr.BENE_ID || fr.Provider_NPI === 'None' || fr.BENE_ID === 'None'

    // 2. Canonical Issue Classification (No artificial data-quality collapse)
    let issueType, issueDescription, contextData = {}

    if (isMissingRequiredSource) {
      // Genuine source data quality defect (Missing NPI / Member ID)
      issueType = 'DATA_QUALITY_MISSING_SOURCE_FIELD'
      issueDescription = `Required source identifier missing for record ${rec.record_id}. No authoritative source value exists.`
      contextData = { layer: 'DATA_QUALITY' }
    } else if (isSlaMissingOutput) {
      // Genuine downstream serialization drop
      issueType = 'SERIALIZATION_MISSING_SLA_OUTPUT'
      issueDescription = `SLA engine produced BREACHED result for ${rec.record_id} but final output artifact has unpopulated SLA status.`
      contextData = { authoritative_result_available: true, layer: 'FINAL_OUTPUT' }
    } else if (isCorrelation) {
      // Genuine correlation break
      issueType = 'CORRELATION_ANALYSIS_DISCREPANCY'
      issueDescription = `Record ${rec.record_id} exhibits correlation break residual outside normal feature relationship bounds.`
      contextData = { layer: 'CORRELATION_ANALYSIS' }
    } else if (isAnomalous) {
      // Genuine ML / Statistical Anomaly Detection finding
      issueType = 'ANOMALY_DETECTION_STATISTICAL_FLAG'
      issueDescription = `Record ${rec.record_id} flagged by detection engine (${rec.anomaly_type || 'ML Isolation Forest Anomaly'}, Severity: ${rec.severity || 'MEDIUM'}).`
      contextData = { layer: 'ANOMALY_DETECTION' }
    } else if (isSlaBreached) {
      // Genuine SLA turnaround breach (Operational SLA layer)
      issueType = 'SLA_BREACH_EXPOSURE'
      issueDescription = `Statutory turnaround SLA deadline breached for ${rec.record_id}. Processing latency exceeded SLA limit.`
      contextData = { layer: 'SLA' }
    } else if (isQuantitySupply) {
      // Genuine Quantity / Days Supply irregularity
      issueType = 'QUANTITY_SUPPLY_ANALYSIS_DISCREPANCY'
      issueDescription = `Dispense quantity / days supply irregularity detected for ${rec.record_id}.`
      contextData = { layer: 'QUANTITY_SUPPLY_ANALYSIS' }
    } else {
      // Normal monitoring record
      issueType = 'ANOMALY_DETECTION_STATISTICAL_FLAG'
      issueDescription = `Record ${rec.record_id} processed within baseline operational tolerances.`
      contextData = { layer: 'ANOMALY_DETECTION' }
    }

    const payload = {
      run_id: runId || 'RUN-CURRENT',
      record_id: rec.record_id,
      issue_type: issueType,
      issue_description: issueDescription,
      evidence: evidenceList,
      root_cause: rec.likely_root_cause || '',
      context_data: contextData,
    }

    setEvalLoading(true)
    evaluateAutoResolution(payload)
      .then(data => setEvaluation(data))
      .catch(err => setError('Evaluation failed: ' + err.message))
      .finally(() => setEvalLoading(false))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedRecord?.record_id, runId])

  /* Load history */
  const loadHistory = () => {
    if (!runId) return
    setHistoryLoading(true)
    getAutoResolutionHistory(runId)
      .then(data => setHistory(data))
      .catch(() => setHistory([]))
      .finally(() => setHistoryLoading(false))
  }

  /* Execute fix — uses evaluation result directly (no need to rebuild payload) */
  const handleApplyFix = async () => {
    if (!evaluation) return
    setConfirmOpen(false)
    setExecLoading(true)
    setError(null)

    const rec = selectedRecordRef.current
    try {
      const result = await executeAutoResolution({
        run_id: runId || 'RUN-CURRENT',
        record_id: rec?.record_id || evaluation.record_id,
        issue_id: evaluation.issue_id,
        issue_type: evaluation.issue_type,
        action_id: evaluation.proposed_action,
        executed_by: 'Operator (Verified)',
        context_data: {
          layer: evaluation.layer,
          evidence: evaluation.evidence,
          root_cause: evaluation.root_cause,
        },
      })
      setExecResult(result)
      loadHistory()
    } catch (err) {
      setError('Execution failed: ' + err.message)
    } finally {
      setExecLoading(false)
    }
  }

  if (evalLoading) {
    return (
      <div className="ares-panel">
        <div className="ares-panel-header">
          <h2>Automatic Resolution</h2>
          <p>Cross-layer auto-fix eligibility evaluation</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '20px' }}>
          <div className="spinner" />
          <span style={{ fontSize: '13px', color: 'var(--gray-500)' }}>Evaluating issue eligibility…</span>
        </div>
      </div>
    )
  }

  const badge = evaluation ? decisionBadge(evaluation.decision_state) : null
  const execBadge = execResult ? statusBadge(execResult.status) : null

  return (
    <div className="ares-panel">
      {/* Panel Header */}
      <div className="ares-panel-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div className="ares-icon">⚙</div>
          <div>
            <h2>Automatic Resolution</h2>
            <p>Cross-layer auto-fix eligibility evaluation across all 14 monitoring layers</p>
          </div>
        </div>
        {evaluation && (
          <div className={`ares-badge ${badge.cls}`}>
            <span>{badge.icon}</span>
            <span>{badge.label}</span>
          </div>
        )}
      </div>

      {error && (
        <div className="ares-error">{error}</div>
      )}

      {evaluation && (
        <div className="ares-body">
          {/* Decision Summary */}
          <div className="ares-decision-card">
            {/* Multi-Signal Telemetry Bar */}
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', paddingBottom: '8px', borderBottom: '1px solid #e2e8f0', marginBottom: '8px' }}>
              <span className={`ares-pill ${(full.ML_Is_Anomalous || full.ISO_Is_Anomaly || selectedRecord?.anomaly_type !== 'Normal') ? 'ares-pill-rollback' : 'ares-pill-yes'}`}>
                ML: {(full.ML_Is_Anomalous || full.ISO_Is_Anomaly || selectedRecord?.anomaly_type !== 'Normal') ? 'ANOMALY' : 'NORMAL'}
              </span>
              <span className={`ares-pill ${full.SLA_Status === 'BREACHED' ? 'ares-pill-no' : 'ares-pill-yes'}`}>
                SLA: {full.SLA_Status || 'ON TRACK'}
              </span>
              <span className={`ares-pill ${(full.Provider_NPI && full.BENE_ID) ? 'ares-pill-yes' : 'ares-pill-no'}`}>
                DQ: {(full.Provider_NPI && full.BENE_ID) ? 'PASS' : 'DEFECT'}
              </span>
              {full.Correlation_Anomaly && (
                <span className="ares-pill ares-pill-warn">CORRELATION BREAK</span>
              )}
            </div>

            <div className="ares-decision-meta">
              <div className="ares-meta-row">
                <span className="ares-meta-label">Issue ID</span>
                <code className="ares-code">{evaluation.issue_id}</code>
              </div>
              <div className="ares-meta-row">
                <span className="ares-meta-label">Layer</span>
                <span className="ares-meta-value">{evaluation.layer?.replace(/_/g, ' ')}</span>
              </div>
              <div className="ares-meta-row">
                <span className="ares-meta-label">Issue Type</span>
                <span className="ares-meta-value">{evaluation.issue_type?.replace(/_/g, ' ')}</span>
              </div>
              <div className="ares-meta-row">
                <span className="ares-meta-label">Proposed Action</span>
                <code className="ares-code ares-code-action">{evaluation.proposed_action}</code>
              </div>
              <div className="ares-meta-row">
                <span className="ares-meta-label">Rollback Available</span>
                <span className={`ares-pill ${evaluation.rollback_available ? 'ares-pill-yes' : 'ares-pill-no'}`}>
                  {evaluation.rollback_available ? 'Yes' : 'No'}
                </span>
              </div>
            </div>

            {/* Root Cause */}
            <div className="ares-section">
              <div className="ares-section-label">Root Cause</div>
              <div className="ares-section-text">{evaluation.root_cause || evaluation.issue_description}</div>
            </div>

            {/* Eligibility Rationale */}
            <div className="ares-section">
              <div className="ares-section-label">Eligibility Determination</div>
              <div className="ares-section-text">{evaluation.eligibility_reason}</div>
            </div>

            {evaluation.safety_rationale && (
              <div className="ares-section">
                <div className="ares-section-label">Safety Rationale</div>
                <div className="ares-section-text">{evaluation.safety_rationale}</div>
              </div>
            )}

            {/* Preconditions */}
            {evaluation.preconditions?.length > 0 && (
              <div className="ares-section">
                <div className="ares-section-label">Preconditions Met</div>
                <ul className="ares-checklist">
                  {evaluation.preconditions.map((pc, i) => (
                    <li key={i}><span className="ares-check">✓</span> {pc}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Evidence Hierarchy Accordion */}
          <div className="ares-accordion">
            <button
              className="ares-accordion-trigger"
              onClick={() => setShowEvidence(v => !v)}
            >
              <span>5-Level Evidence Hierarchy ({evaluation.evidence?.length || 0} Items)</span>
              <span>{showEvidence ? '▲' : '▼'}</span>
            </button>
            {showEvidence && (
              <div className="ares-evidence-list">
                {(evaluation.evidence || []).length === 0 && (
                  <div className="ares-empty">No evidence items attached.</div>
                )}
                {(evaluation.evidence || []).map((ev, i) => {
                  const auth = EVIDENCE_AUTHORITY_LABELS[ev.authority] || EVIDENCE_AUTHORITY_LABELS.LLM
                  return (
                    <div key={i} className="ares-evidence-item" style={{ borderLeftColor: auth.color }}>
                      <div className="ares-evidence-header">
                        <span className="ares-authority-badge" style={{ color: auth.color, background: auth.bg }}>
                          {auth.label}
                        </span>
                        <code className="ares-code" style={{ fontSize: '11px' }}>{ev.source} · {ev.field}</code>
                      </div>
                      <div className="ares-evidence-value">
                        {ev.value !== null && ev.value !== undefined ? String(ev.value) : <em style={{ color: 'var(--gray-400)' }}>NULL</em>}
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Execution Result */}
          {execResult && (
            <div className={`ares-exec-result ${execResult.status === 'AUTO_FIXED' ? 'ares-exec-success' : execResult.status === 'FIX_FAILED_ROLLED_BACK' ? 'ares-exec-rollback' : 'ares-exec-info'}`}>
              <div className="ares-exec-result-header">
                <span className="ares-exec-result-icon">{execBadge?.icon}</span>
                <strong>{execBadge?.label}</strong>
                <code style={{ marginLeft: 'auto', fontSize: '11px' }}>{execResult.fix_id}</code>
              </div>
              {execResult.validation_details?.checks && (
                <ul className="ares-exec-checks">
                  {execResult.validation_details.checks.map((c, i) => (
                    <li key={i}>
                      <span className={c.status === 'PASS' ? 'ares-check-pass' : 'ares-check-fail'}>
                        {c.status === 'PASS' ? '✓' : '✗'}
                      </span>
                      {' '}{c.check}
                    </li>
                  ))}
                </ul>
              )}
              {execResult.error_message && (
                <div style={{ marginTop: '8px', fontSize: '12px', color: '#b91c1c' }}>
                  {execResult.error_message}
                </div>
              )}
              {execResult.before_state && execResult.after_state && execResult.status === 'AUTO_FIXED' && (
                <div className="ares-diff">
                  <div className="ares-diff-col">
                    <div className="ares-diff-label">Before</div>
                    <pre className="ares-diff-pre">{JSON.stringify(execResult.before_state?.full_record || {}, null, 2)}</pre>
                  </div>
                  <div className="ares-diff-col">
                    <div className="ares-diff-label">After</div>
                    <pre className="ares-diff-pre ares-diff-after">{JSON.stringify(execResult.after_state?.full_record || {}, null, 2)}</pre>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Confirmation Modal */}
          {confirmOpen && (
            <div className="ares-confirm-overlay">
              <div className="ares-confirm-modal">
                <div className="ares-confirm-title">⚙ Confirm Auto-Fix Execution</div>
                <div className="ares-confirm-body">
                  <div><strong>Record:</strong> {evaluation.record_id}</div>
                  <div><strong>Action:</strong> <code>{evaluation.proposed_action}</code></div>
                  <div><strong>Layer:</strong> {evaluation.layer?.replace(/_/g, ' ')}</div>
                  <div style={{ marginTop: '12px', fontSize: '12px', color: 'var(--gray-500)' }}>
                    A pre-fix snapshot will be taken. If post-fix validation fails, the change will be automatically rolled back.
                  </div>
                </div>
                <div className="ares-confirm-actions">
                  <button className="ares-btn-cancel" onClick={() => setConfirmOpen(false)}>Cancel</button>
                  <button className="ares-btn-apply" onClick={handleApplyFix}>Apply Fix</button>
                </div>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="ares-action-row">
            {evaluation.auto_fix_eligible && !execResult && !execLoading && (
              <button
                className="ares-btn-primary"
                onClick={() => setConfirmOpen(true)}
              >
                ⚙ Apply Automatic Fix
              </button>
            )}
            {execLoading && (
              <button className="ares-btn-primary" disabled>
                <span className="spinner-small" /> Executing…
              </button>
            )}
            {execResult && (
              <button
                className="ares-btn-secondary"
                onClick={() => { setExecResult(null); setConfirmOpen(false) }}
              >
                ↺ Re-Evaluate
              </button>
            )}
            <button
              className="ares-btn-outline"
              onClick={() => { setShowHistory(v => !v); if (!showHistory) loadHistory() }}
            >
              {showHistory ? 'Hide' : 'View'} Audit History
            </button>
          </div>
        </div>
      )}

      {/* Auto-Resolution Audit History Table */}
      {showHistory && (
        <div className="ares-history">
          <div className="ares-history-header">
            <h3>Auto-Resolution Audit History</h3>
            <button className="ares-btn-outline" style={{ fontSize: '11px', padding: '4px 12px' }} onClick={loadHistory}>
              ↺ Refresh
            </button>
          </div>
          {historyLoading ? (
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center', padding: '12px' }}>
              <div className="spinner" />
              <span style={{ fontSize: '12px', color: 'var(--gray-500)' }}>Loading history…</span>
            </div>
          ) : history.length === 0 ? (
            <div className="ares-empty">No remediations recorded yet.</div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table className="ares-history-table">
                <thead>
                  <tr>
                    <th>Fix ID</th>
                    <th>Record</th>
                    <th>Layer</th>
                    <th>Action</th>
                    <th>Status</th>
                    <th>Validation</th>
                    <th>Time</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map(h => {
                    const sb = statusBadge(h.status)
                    return (
                      <tr key={h.fix_id}>
                        <td><code style={{ fontSize: '10px' }}>{h.fix_id?.slice(-14)}</code></td>
                        <td><code style={{ fontSize: '11px' }}>{h.record_id}</code></td>
                        <td style={{ fontSize: '11px' }}>{h.layer?.replace(/_/g, ' ')}</td>
                        <td><code style={{ fontSize: '10px' }}>{h.action_id}</code></td>
                        <td>
                          <span className={`ares-pill ${h.status === 'AUTO_FIXED' ? 'ares-pill-yes' : h.status === 'FIX_FAILED_ROLLED_BACK' ? 'ares-pill-rollback' : 'ares-pill-warn'}`}>
                            {sb.icon} {sb.label}
                          </span>
                        </td>
                        <td>
                          <span className={`ares-pill ${h.validation_status === 'PASS' ? 'ares-pill-yes' : 'ares-pill-no'}`}>
                            {h.validation_status}
                          </span>
                        </td>
                        <td style={{ fontSize: '11px', color: 'var(--gray-400)' }}>
                          {h.created_at ? new Date(h.created_at).toLocaleTimeString() : '—'}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/* ─── Main Page ─── */
export default function RecommendationPage() {
  const { anomalies, statistics, isLoading, error } = useMedlyticsData()
  const [selectedId, setSelectedId] = useState(null)
  const [selectedRecord, setSelectedRecord] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [showMonitoringDetails, setShowMonitoringDetails] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [runId, setRunId] = useState(null)

  // Derive run ID from statistics
  useEffect(() => {
    if (statistics?.run_id) setRunId(statistics.run_id)
  }, [statistics])

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
    getAnomalyDetail(selectedId)
      .then(data => setSelectedRecord(data))
      .catch(err => console.error('Failed to load recommendation context:', err))
      .finally(() => setDetailLoading(false))
  }, [selectedId])

  const handleGenerate = () => {
    if (!selectedId) return
    setIsGenerating(true)
    setTimeout(() => {
      getAnomalyDetail(selectedId)
        .then(data => setSelectedRecord(data))
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
  const isAnomalous = full.ML_Is_Anomalous === true || full.ISO_Is_Anomaly === true || selectedRecord?.severity === 'HIGH' || selectedRecord?.severity === 'MEDIUM'
  const slaStatus = full.SLA_Status ?? full.status ?? 'ON TRACK'
  const dqStatus = (statistics?.overall_data_quality_score ?? 88.8) >= 80 ? 'PASS' : 'WARNING'
  const evidenceList = Array.isArray(selectedRecord?.evidence) && selectedRecord.evidence.length > 0 ? selectedRecord.evidence : selectedRecord?.primary_signal ? [selectedRecord.primary_signal] : []
  const observedFacts = Array.isArray(selectedRecord?.observed_facts) ? selectedRecord.observed_facts : []
  const filtered = anomalies.filter(a => !searchTerm || (a.record_id?.toLowerCase().includes(searchTerm.toLowerCase())))

  return (
    <div className="ml-page">
      {/* Header */}
      <div className="ml-page-heading">
        <h1>Recommendation Engine</h1>
        <p>Evidence-grounded operational recommendations with cross-layer automated resolution capabilities.</p>
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

        {/* Right: Analysis Content */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          {detailLoading ? (
            <div className="loading-container">
              <div className="spinner" />
              <p className="loading-text">Loading record analysis context...</p>
            </div>
          ) : selectedRecord ? (
            <>
              {/* Record Under Analysis */}
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
                  {isGenerating ? (<><span className="spinner-small" /> Analyzing...</>) : 'Generate Recommendation'}
                </button>
              </div>

              {/* Monitoring Context */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <div style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--gray-400)', fontWeight: 600, letterSpacing: '0.8px' }}>Monitoring Context</div>
                  <button onClick={() => setShowMonitoringDetails(o => !o)} style={{ background: 'none', border: 'none', color: 'var(--navy-500)', fontSize: '12px', cursor: 'pointer', padding: 0 }}>
                    {showMonitoringDetails ? '▲ Hide Details' : '▼ View Details'}
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
                {showMonitoringDetails && (
                  <div className="ml-info-card" style={{ marginTop: '10px' }}>
                    <div className="ml-field-grid">
                      <div className="ml-field-row">
                        <span className="ml-field-label">Anomaly Model</span>
                        <span className="ml-field-value">Isolation Forest + Correlation</span>
                      </div>
                      <div className="ml-field-row">
                        <span className="ml-field-label">Primary Signal</span>
                        <span className="ml-field-value">{selectedRecord.primary_signal || 'No anomalous signal'}</span>
                      </div>
                      <div className="ml-field-row">
                        <span className="ml-field-label">SLA Target</span>
                        <span className="ml-field-value">{full.sla_target_days ? `${full.sla_target_days} Days` : '2.0 Days'}</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* AUTO-RESOLUTION PANEL */}
              <AutoResolutionPanel selectedRecord={selectedRecord} runId={runId} />

              {/* AI Recommendation */}
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
                      isAnomalous ? 'Initiate secondary clinical audit on authorization link and verify provider billing frequency.' : 'Routine adjudication approved. No operational hold required.'
                    )}
                  </div>
                  {selectedRecord.impact && (
                    <div style={{ background: 'var(--surface-inset)', border: '1px solid var(--border-light)', borderRadius: 'var(--radius-sm)', padding: '12px 16px', marginTop: '12px' }}>
                      <div style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--gray-400)', fontWeight: 600, letterSpacing: '0.6px', marginBottom: '4px' }}>Operational Impact</div>
                      <div style={{ fontSize: '13px', color: 'var(--gray-700)' }}>{selectedRecord.impact}</div>
                    </div>
                  )}
                </div>
              </div>

              {/* Evidence Retrieved */}
              <div className="ml-info-card">
                <div className="ml-info-card-header">
                  <div className="ml-info-card-title">
                    <h2>Evidence Retrieved</h2>
                    <p>Relevant knowledge base &amp; policy evidence retrieved by the RAG pipeline</p>
                  </div>
                </div>
                <div className="ml-info-card-body">
                  {evidenceList.length === 0 ? (
                    <div className="ml-empty">No policy evidence citations attached.</div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      {evidenceList.map((evText, i) => (
                        <div key={i} style={{ background: 'var(--surface-inset)', border: '1px solid var(--border-light)', borderRadius: 'var(--radius-sm)', padding: '14px 16px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                            <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--navy-800)' }}>EVIDENCE 0{i + 1}</span>
                            <span style={{ fontSize: '10px', textTransform: 'uppercase', background: 'var(--navy-100)', color: 'var(--navy-700)', padding: '2px 8px', borderRadius: '4px', fontWeight: 600 }}>Retrieved Policy</span>
                          </div>
                          <div style={{ fontSize: '13px', color: 'var(--gray-700)', lineHeight: '1.5' }}>{evText}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Supporting Signals */}
              <div className="ml-info-card">
                <div className="ml-info-card-header">
                  <div className="ml-info-card-title">
                    <h2>Supporting Monitoring Signals</h2>
                    <p>Active telemetry across Anomaly, SLA, and Quality engines</p>
                  </div>
                </div>
                <div className="ml-info-card-body">
                  <div className="ml-signals-list">
                    <div className="ml-signal-item"><span className="ml-signal-dot" /><div><strong>Anomaly Engine:</strong> {selectedRecord.anomaly_type || 'ML Multivariate'} (Severity: {selectedRecord.severity || 'Normal'})</div></div>
                    <div className="ml-signal-item"><span className="ml-signal-dot" /><div><strong>SLA Engine:</strong> Status: {slaStatus} · Target: {full.sla_target_days ? `${full.sla_target_days} Days` : '2.0 Days'}</div></div>
                    <div className="ml-signal-item"><span className="ml-signal-dot" /><div><strong>Data Quality Engine:</strong> Score: {fmtNum(statistics?.overall_data_quality_score ?? 88.8, 1)} / 100 · Status: {dqStatus}</div></div>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="ml-empty">Select a record to generate an evidence-grounded recommendation.</div>
          )}
        </div>
      </div>
    </div>
  )
}
