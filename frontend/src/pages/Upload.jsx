import React, { useState } from 'react'
import { useStore } from '../hooks/useStore'
import { uploadAndAnalyze } from '../services/api'
import './Upload.css'

const PROCESSING_STAGES = [
  { label: 'File uploaded',               status: 'Received and validated' },
  { label: 'Running anomaly detection',   status: 'Statistical, Isolation Forest, Correlation' },
  { label: 'Running RCA / RAG analysis',  status: 'Root cause classification' },
  { label: 'Saving anomaly results',      status: 'Persisting to database' },
  { label: 'Analysis complete',           status: 'Dashboard ready' },
]

// SVG icons (inline, no emoji)
const UploadIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <polyline points="16 16 12 12 8 16" />
    <line x1="12" y1="12" x2="12" y2="21" />
    <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3" />
  </svg>
)

const FileIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <polyline points="14 2 14 8 20 8" />
  </svg>
)

const CheckIcon = () => (
  <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" fill="none" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <polyline points="20 6 9 17 4 12" />
  </svg>
)

export default function Upload() {
  const [dragActive, setDragActive] = useState(false)
  const [selectedFile, setSelectedFile] = useState(null)
  const setCurrentRun = useStore(state => state.setCurrentRun)
  const setIsUploading = useStore(state => state.setIsUploading)
  const setError = useStore(state => state.setError)
  const setStatistics = useStore(state => state.setStatistics)
  const isUploading = useStore(state => state.isUploading)
  const error = useStore(state => state.error)

  const [processingStage, setProcessingStage] = useState(0)

  const handleDragEnter = (e) => { e.preventDefault(); e.stopPropagation(); setDragActive(true) }
  const handleDragLeave = (e) => { e.preventDefault(); e.stopPropagation(); setDragActive(false) }
  const handleDragOver  = (e) => { e.preventDefault(); e.stopPropagation() }

  const handleDrop = (e) => {
    e.preventDefault(); e.stopPropagation(); setDragActive(false)
    const files = e.dataTransfer.files
    if (files && files.length > 0) handleFileSelect(files[0])
  }

  const handleFileSelect = (file) => {
    const validExtensions = ['csv', 'xls', 'xlsx']
    const fileExt = file.name.split('.').pop().toLowerCase()
    if (!validExtensions.includes(fileExt)) {
      setError(`Invalid file format: .${fileExt}. Supported: CSV, XLS, XLSX`)
      setSelectedFile(null)
      return
    }
    if (file.size > 100 * 1024 * 1024) {
      setError('File too large. Maximum size: 100MB')
      setSelectedFile(null)
      return
    }
    setSelectedFile(file)
    setError(null)
  }

  const handleFileInputChange = (e) => {
    if (e.target.files && e.target.files.length > 0) handleFileSelect(e.target.files[0])
  }

  const handleAnalyze = async () => {
    if (!selectedFile) { setError('Please select a file'); return }
    setIsUploading(true)
    setError(null)
    setProcessingStage(0)
    try {
      const stageInterval = setInterval(() => {
        setProcessingStage(prev => {
          if (prev < PROCESSING_STAGES.length - 1) return prev + 1
          clearInterval(stageInterval)
          return prev
        })
      }, 1000)
      const result = await uploadAndAnalyze(selectedFile)
      clearInterval(stageInterval)
      setProcessingStage(PROCESSING_STAGES.length - 1)
      setCurrentRun(result)
      setStatistics({ totalRecords: result.total_records, totalAnomalies: result.total_anomalies, bySeverity: result.severity_summary })
      setSelectedFile(null)
    } catch (err) {
      setError(err.message || 'Analysis failed. Please check the backend logs.')
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <div className="upload-container">
      {/* Nav bar */}
      <header className="upload-header">
        <div className="upload-header-brand">
          <span className="upload-header-uc10">UC10</span>
          <span className="upload-header-divider" />
          <span className="upload-header-title">Claims &amp; Authorization Anomaly Monitor</span>
        </div>
      </header>

      <div className="upload-content">
        {!isUploading ? (
          <>
            <h1 className="upload-content-title">Claims Data Analysis</h1>
            <p className="upload-content-subtitle">
              Upload a claims, pharmacy or authorization dataset to begin anomaly monitoring.
            </p>

            {/* Drop zone */}
            <div
              className={`upload-dropzone${dragActive ? ' active' : ''}`}
              onDragEnter={handleDragEnter}
              onDragLeave={handleDragLeave}
              onDragOver={handleDragOver}
              onDrop={handleDrop}
            >
              <div className="dropzone-content">
                <div className="dropzone-icon"><UploadIcon /></div>
                <h3>Drag &amp; drop your file here</h3>
                <p>or</p>
                <label className="browse-button">
                  Browse Files
                  <input
                    type="file"
                    onChange={handleFileInputChange}
                    accept=".csv,.xls,.xlsx"
                    disabled={isUploading}
                    style={{ display: 'none' }}
                  />
                </label>
                <p className="file-format-info">CSV / XLS / XLSX &nbsp;·&nbsp; Maximum 100 MB</p>
              </div>
            </div>

            {/* Selected file row */}
            {selectedFile && (
              <div className="file-selected">
                <div className="file-info-box">
                  <div className="file-icon-wrap"><FileIcon /></div>
                  <div className="file-details">
                    <p className="file-name">{selectedFile.name}</p>
                    <p className="file-size">{(selectedFile.size / 1024 / 1024).toFixed(2)} MB</p>
                  </div>
                </div>
                <button className="analyze-button" onClick={handleAnalyze} disabled={isUploading}>
                  {isUploading ? <><span className="spinner-small" /> Analyzing...</> : 'Start Analysis'}
                </button>
              </div>
            )}

            {error && (
              <div className="error-message" role="alert">
                <svg width="16" height="16" viewBox="0 0 24 24" stroke="currentColor" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
                </svg>
                {error}
              </div>
            )}

            {/* How it works */}
            <div className="upload-info">
              <h3>How It Works</h3>
              <ol>
                <li><strong>Upload File:</strong> Select a CSV or Excel file with claims data</li>
                <li><strong>Anomaly Detection:</strong> ML pipeline detects suspicious patterns</li>
                <li><strong>Root Cause Analysis:</strong> LLM analyzes likely causes</li>
                <li><strong>View Results:</strong> Explore anomalies with detailed explanations</li>
              </ol>
            </div>
          </>
        ) : (
          <div className="processing-container">
            <h2>Analysis in Progress</h2>
            <p className="processing-subtitle">Processing claims dataset — please wait...</p>

            <div className="processing-stages">
              {PROCESSING_STAGES.map((stage, index) => {
                const isDone    = index < processingStage
                const isCurrent = index === processingStage
                const isPending = index > processingStage
                const cls = isDone ? 'completed' : isCurrent ? 'current' : 'pending'
                return (
                  <div key={index} className={`stage ${cls}`}>
                    <div className="stage-indicator">
                      {isDone    ? <CheckIcon /> :
                       isCurrent ? <span className="spinner-sm" /> :
                                   <span style={{fontSize:'12px'}}>{index + 1}</span>}
                    </div>
                    {index < PROCESSING_STAGES.length - 1 && <div className="stage-connector" />}
                    <div className="stage-body">
                      <span className="stage-name">{stage.label}</span>
                      {(isDone || isCurrent) && <span className="stage-status-text">{isDone ? 'Complete' : stage.status}</span>}
                    </div>
                  </div>
                )
              })}
            </div>
            <p className="processing-note">This may take a few minutes depending on file size...</p>
          </div>
        )}
      </div>
    </div>
  )
}
