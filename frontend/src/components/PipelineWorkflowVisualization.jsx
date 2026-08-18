import React, { useState } from 'react'
import './PipelineWorkflowVisualization.css'

/**
 * PipelineWorkflowVisualization.jsx
 * 
 * STRICTLY PRESENTATIONAL component rendering the standard technical pipeline workflow.
 * Displays the 8-stage processing lifecycle of the MEDLYTICS architecture.
 * Does NOT execute, trigger, or control any pipeline stages or backend APIs.
 */
export default function PipelineWorkflowVisualization() {
  const [isDqGatesOpen, setIsDqGatesOpen] = useState(false)

  const dqDimensions = [
    'Completeness',
    'Validity',
    'Consistency',
    'Uniqueness',
    'Accuracy',
    'Timeliness',
    'Referential Integrity',
    'Conformity',
    'Range Validation',
    'Temporal Integrity',
  ]

  const stages = [
    {
      id: 'ingestion',
      stepNumber: 1,
      name: 'DATA INGESTION',
      description: 'Ingesting and validating the uploaded healthcare dataset.',
      status: 'COMPLETED',
    },
    {
      id: 'feature_engineering',
      stepNumber: 2,
      name: 'FEATURE ENGINEERING',
      description: 'Generating analytical features required by downstream monitoring engines.',
      status: 'COMPLETED',
    },
    {
      id: 'data_quality',
      stepNumber: 3,
      name: 'DATA QUALITY VALIDATION & QUALITY GATES',
      description: 'Validating completeness, validity, consistency, and temporal integrity before downstream analysis.',
      status: 'COMPLETED',
      hasExpandableGates: true,
    },
    {
      id: 'anomaly_detection',
      stepNumber: 4,
      name: 'ANOMALY DETECTION',
      description: 'Detecting statistically and machine-learning-driven deviations in claims and authorization behavior.',
      status: 'COMPLETED',
    },
    {
      id: 'sla_compliance',
      stepNumber: 5,
      name: 'SLA COMPLIANCE & RISK ASSESSMENT',
      description: 'Evaluating processing turnaround against applicable SLA thresholds.',
      status: 'COMPLETED',
    },
    {
      id: 'evidence_rag',
      stepNumber: 6,
      name: 'EVIDENCE RETRIEVAL (RAG)',
      description: 'Retrieving policy, operational, and record-level evidence to ground downstream analysis.',
      status: 'COMPLETED',
    },
    {
      id: 'llm_recommendation',
      stepNumber: 7,
      name: 'LLM RECOMMENDATION & FIX',
      description: 'Generating evidence-grounded recommendations and corrective actions using the LLM.',
      status: 'COMPLETED',
    },
    {
      id: 'autofix_agent',
      stepNumber: 8,
      name: 'AUTOFIX AGENT',
      description: 'Applying validated corrective actions to resolve identified data and processing issues.',
      status: 'COMPLETED',
    },
  ]

  return (
    <div className="ml-workflow-container" id="standard-technical-pipeline-workflow">
      {/* Container Header */}
      <div className="ml-workflow-header">
        <div className="ml-workflow-header-content">
          <div className="ml-workflow-eyebrow">SYSTEM ARCHITECTURE MAP</div>
          <h2 className="ml-workflow-title">STANDARD TECHNICAL PIPELINE WORKFLOW</h2>
          <p className="ml-workflow-subtitle">
            Visual map of the end-to-end processing lifecycle from dataset ingestion through automated remediation
          </p>
        </div>
        <div className="ml-workflow-header-badge">
          <span className="ml-workflow-pill">8 STAGES VALIDATED</span>
        </div>
      </div>

      {/* Workflow Stages List */}
      <div className="ml-workflow-stages">
        {stages.map((stage, idx) => (
          <div key={stage.id} className="ml-workflow-stage-wrapper">
            <div className="ml-workflow-stage-item">
              {/* Left Column: Icon & Stage Name / Description */}
              <div className="ml-workflow-stage-main">
                <div className="ml-workflow-check-circle" aria-label="Completed">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                </div>

                <div className="ml-workflow-stage-text">
                  <div className="ml-workflow-stage-name">
                    {stage.name}
                  </div>
                  <div className="ml-workflow-stage-desc">
                    {stage.description}
                  </div>

                  {/* Expandable subsection for Data Quality Quality Gates */}
                  {stage.hasExpandableGates && (
                    <div className="ml-workflow-dq-gates-section">
                      <button
                        type="button"
                        className="ml-workflow-dq-toggle-btn"
                        onClick={() => setIsDqGatesOpen(prev => !prev)}
                        aria-expanded={isDqGatesOpen}
                      >
                        <span className="ml-workflow-toggle-icon">{isDqGatesOpen ? '▼' : '▶'}</span>
                        <span>Data Quality Quality Gates (10 Dimensions &amp; Gates)</span>
                      </button>

                      {isDqGatesOpen && (
                        <div className="ml-workflow-dq-gates-panel">
                          <div className="ml-workflow-dq-grid">
                            {dqDimensions.map(dim => (
                              <div key={dim} className="ml-workflow-dq-item">
                                <span className="ml-workflow-dq-check">✓</span>
                                <span className="ml-workflow-dq-label">{dim}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Right Column: Status */}
              <div className="ml-workflow-stage-status">
                <span className="ml-workflow-status-badge">
                  {stage.status}
                </span>
              </div>
            </div>

            {/* Separator between stages */}
            {idx < stages.length - 1 && (
              <div className="ml-workflow-connector" />
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
