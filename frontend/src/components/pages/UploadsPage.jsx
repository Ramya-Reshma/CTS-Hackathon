import React, { useState, useEffect, useRef } from 'react'
import { uploadAndAnalyze, getRuns } from '../../services/api'
import { useStore } from '../../hooks/useStore'
import { fmtNum } from '../../utils/statusUtils'
import './shared-pages.css'

export default function UploadsPage({ onNavigateToOverview }) {
  const [runs, setRuns] = useState([])
  const [loadingRuns, setLoadingRuns] = useState(false)
  const [selectedFile, setSelectedFile] = useState(null)
  const [uploadStatus, setUploadStatus] = useState('idle') // idle, uploading, processing, completed, failed
  const [errorMessage, setErrorMessage] = useState(null)
  const [isDragOver, setIsDragOver] = useState(false)
  const fileInputRef = useRef(null)

  const currentRun = useStore(state => state.currentRun)
  const setCurrentRun = useStore(state => state.setCurrentRun)

  // Fetch runs list from backend API
  const fetchRunsList = async () => {
    setLoadingRuns(true)
    try {
      const data = await getRuns({ page: 1, pageSize: 30 })
      setRuns(data.records || data.runs || (Array.isArray(data) ? data : []))
    } catch (err) {
      console.error('Failed to load runs history:', err)
    } finally {
      setLoadingRuns(false)
    }
  }

  useEffect(() => {
    fetchRunsList()
  }, [])

  const handleFileChange = (e) => {
    const file = e.target.files?.[0]
    if (file) {
      const validExts = ['.csv', '.xls', '.xlsx']
      const ext = file.name.toLowerCase().slice(file.name.lastIndexOf('.'))
      if (!validExts.includes(ext)) {
        setErrorMessage('Unsupported file format. Please select a CSV, XLS, or XLSX file.')
        return
      }
      setSelectedFile(file)
      setErrorMessage(null)
      setUploadStatus('idle')
    }
  }

  const handleDragOver = (e) => {
    e.preventDefault()
    setIsDragOver(true)
  }

  const handleDragLeave = (e) => {
    e.preventDefault()
    setIsDragOver(false)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setIsDragOver(false)
    const file = e.dataTransfer.files?.[0]
    if (file) {
      const validExts = ['.csv', '.xls', '.xlsx']
      const ext = file.name.toLowerCase().slice(file.name.lastIndexOf('.'))
      if (!validExts.includes(ext)) {
        setErrorMessage('Unsupported file format. Please drop a CSV, XLS, or XLSX file.')
        return
      }
      setSelectedFile(file)
      setErrorMessage(null)
      setUploadStatus('idle')
    }
  }

  const handleRunMonitoring = async () => {
    if (!selectedFile) return
    setUploadStatus('processing')
    setErrorMessage(null)

    try {
      const result = await uploadAndAnalyze(selectedFile)
      setUploadStatus('completed')

      // Update global current run
      if (result.run_id) {
        const runPayload = {
          id: result.run_id,
          run_id: result.run_id,
          dataset_id: result.dataset_id,
          filename: result.filename || selectedFile.name,
          total_records: result.total_records,
          anomaly_count: result.total_anomalies,
          severity_summary: result.severity_summary,
          processing_status: result.status,
        }
        setCurrentRun(runPayload)
      }

      // Refresh historical runs table
      await fetchRunsList()

      // Clear file selection after brief moment
      setTimeout(() => {
        setSelectedFile(null)
        setUploadStatus('idle')
        if (onNavigateToOverview) {
          onNavigateToOverview()
        }
      }, 1000)

    } catch (err) {
      console.error('Monitoring run failed:', err)
      setUploadStatus('failed')
      setErrorMessage(err.message || 'Pipeline execution failed during analysis.')
    }
  }

  const handleSelectRun = (run) => {
    const runPayload = {
      id: run.id,
      run_id: run.id,
      dataset_id: run.dataset_id,
      filename: run.filename,
      total_records: run.total_records,
      anomaly_count: run.anomaly_count,
      severity_summary: run.severity_summary,
      processing_status: run.processing_status,
      created_at: run.created_at,
    }
    setCurrentRun(runPayload)
    if (onNavigateToOverview) {
      onNavigateToOverview()
    }
  }

  const formatFileSize = (bytes) => {
    if (!bytes) return 'Unknown size'
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A'
    try {
      const d = new Date(dateStr)
      return d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    } catch {
      return dateStr
    }
  }

  return (
    <div className="ml-page">
      {/* Page Header */}
      <div className="ml-page-heading">
        <h1>Uploads</h1>
        <p>Upload healthcare datasets and manage monitoring runs.</p>
      </div>

      {/* Error Alert */}
      {errorMessage && (
        <div className="error-banner" role="alert" style={{ marginBottom: '4px' }}>
          <span><strong>Upload Failed:</strong> {errorMessage}</span>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────── */}
      {/* SECTION 1: UPLOAD DATASET CARD                             */}
      {/* ─────────────────────────────────────────────────────────── */}
      <div className="ml-section-label">Upload Dataset</div>

      <div className="ml-info-card">
        <div className="ml-info-card-header">
          <div className="ml-info-card-title">
            <h2>Data Ingestion &amp; Pipeline Execution</h2>
            <p>Upload raw or normalized healthcare claims and authorization CSV records for end-to-end monitoring</p>
          </div>
          <span className="type-badge" style={{ fontSize: '11px' }}>Supported: CSV · XLS · XLSX</span>
        </div>

        <div style={{ padding: '24px' }}>
          {/* Dropzone Area */}
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            style={{
              border: isDragOver ? '2px dashed var(--navy-600)' : '2px dashed var(--gray-200)',
              borderRadius: 'var(--radius-md)',
              padding: '36px 20px',
              textAlign: 'center',
              background: isDragOver ? 'var(--navy-50)' : 'var(--surface-inset)',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.xls,.xlsx"
              style={{ display: 'none' }}
              onChange={handleFileChange}
            />

            <div style={{ width: '48px', height: '48px', margin: '0 auto 12px', background: 'var(--navy-100)', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--navy-700)' }}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
            </div>

            <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--navy-900)', marginBottom: '4px' }}>
              Drag &amp; drop your healthcare claims file here
            </div>
            <div style={{ fontSize: '12px', color: 'var(--gray-400)', marginBottom: '14px' }}>
              or
            </div>
            <button
              type="button"
              className="primary-button"
              style={{ padding: '7px 18px', fontSize: '12px' }}
              onClick={(e) => { e.stopPropagation(); fileInputRef.current?.click() }}
            >
              Browse Files
            </button>
            <div style={{ fontSize: '11px', color: 'var(--gray-400)', marginTop: '12px' }}>
              Supported formats: CSV (.csv) · Excel (.xls, .xlsx)
            </div>
          </div>

          {/* Selected File Card & Run Action */}
          {selectedFile && (
            <div style={{ marginTop: '18px', background: 'var(--surface-card)', border: '1px solid var(--border-light)', borderRadius: 'var(--radius-md)', padding: '16px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                <div style={{ width: '38px', height: '38px', background: 'var(--navy-50)', borderRadius: '6px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--navy-700)' }}>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                    <line x1="16" y1="13" x2="8" y2="13" />
                    <line x1="16" y1="17" x2="8" y2="17" />
                  </svg>
                </div>
                <div>
                  <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--navy-900)' }}>
                    {selectedFile.name}
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--gray-400)', marginTop: '2px' }}>
                    {selectedFile.name.toLowerCase().endsWith('.xlsx') || selectedFile.name.toLowerCase().endsWith('.xls') ? 'Excel' : 'CSV'} · {formatFileSize(selectedFile.size)} · Ready for analysis
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <button
                  type="button"
                  className="secondary-button"
                  style={{ padding: '8px 14px', fontSize: '12px' }}
                  onClick={() => { setSelectedFile(null); setUploadStatus('idle'); setErrorMessage(null); }}
                  disabled={uploadStatus === 'processing'}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="primary-button"
                  style={{ padding: '8px 20px', fontSize: '12px', minWidth: '130px' }}
                  onClick={handleRunMonitoring}
                  disabled={uploadStatus === 'processing'}
                >
                  {uploadStatus === 'processing' ? 'Running Analysis...' : 'Run Monitoring'}
                </button>
              </div>
            </div>
          )}

          {/* Processing Status Banner */}
          {uploadStatus === 'processing' && (
            <div style={{ marginTop: '14px', padding: '12px 16px', background: 'var(--navy-50)', border: '1px solid var(--navy-200)', borderRadius: 'var(--radius-sm)', display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div className="spinner" style={{ width: '16px', height: '16px', borderWidth: '2px' }} />
              <div style={{ fontSize: '12px', color: 'var(--navy-800)', fontWeight: 500 }}>
                Executing ML Anomaly, SLA Temporal, and Data Quality monitoring pipeline...
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────── */}
      {/* SECTION 2: RECENT UPLOADS & RUN HISTORY                    */}
      {/* ─────────────────────────────────────────────────────────── */}
      <div className="ml-section-label" style={{ marginTop: '16px' }}>Recent Uploads &amp; Run History</div>

      <div className="ml-info-card">
        <div className="ml-info-card-header">
          <div className="ml-info-card-title">
            <h2>Monitoring Run History</h2>
            <p>Select any previous execution run to review monitoring dimensions</p>
          </div>
          <button
            type="button"
            className="secondary-button"
            style={{ padding: '5px 12px', fontSize: '11px' }}
            onClick={fetchRunsList}
          >
            Refresh
          </button>
        </div>

        {loadingRuns ? (
          <div className="loading-container">
            <div className="spinner" />
            <p className="loading-text">Loading run history...</p>
          </div>
        ) : runs.length === 0 ? (
          <div className="ml-empty" style={{ padding: '40px 20px' }}>
            <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--navy-900)', marginBottom: '4px' }}>
              NO DATASETS UPLOADED
            </div>
            <div style={{ fontSize: '12px', color: 'var(--gray-400)', marginBottom: '14px' }}>
              Upload a healthcare dataset to begin monitoring.
            </div>
            <button
              type="button"
              className="primary-button"
              style={{ padding: '6px 16px', fontSize: '12px' }}
              onClick={() => fileInputRef.current?.click()}
            >
              Upload Dataset
            </button>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
              <thead>
                <tr style={{ background: 'var(--gray-50)', borderBottom: '1px solid var(--border-light)', textAlign: 'left' }}>
                  <th style={{ padding: '10px 16px', fontWeight: 600, color: 'var(--gray-500)' }}>Dataset</th>
                  <th style={{ padding: '10px 16px', fontWeight: 600, color: 'var(--gray-500)' }}>Records</th>
                  <th style={{ padding: '10px 16px', fontWeight: 600, color: 'var(--gray-500)' }}>Anomalies</th>
                  <th style={{ padding: '10px 16px', fontWeight: 600, color: 'var(--gray-500)' }}>Run ID</th>
                  <th style={{ padding: '10px 16px', fontWeight: 600, color: 'var(--gray-500)' }}>Status</th>
                  <th style={{ padding: '10px 16px', fontWeight: 600, color: 'var(--gray-500)' }}>Created Time</th>
                  <th style={{ padding: '10px 16px', fontWeight: 600, color: 'var(--gray-500)', textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {runs.map(run => {
                  const isCurrent = currentRun?.run_id === run.id || currentRun?.id === run.id
                  return (
                    <tr
                      key={run.id}
                      style={{
                        borderBottom: '1px solid var(--gray-100)',
                        background: isCurrent ? 'var(--navy-50)' : 'transparent',
                        transition: 'background 0.15s ease',
                      }}
                    >
                      <td style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--navy-900)' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--navy-600)' }}>
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                            <polyline points="14 2 14 8 20 8" />
                          </svg>
                          {run.filename}
                          {isCurrent && (
                            <span style={{ fontSize: '10px', background: 'var(--navy-700)', color: '#fff', padding: '1px 6px', borderRadius: '3px', fontWeight: 600 }}>
                              ACTIVE
                            </span>
                          )}
                        </div>
                      </td>
                      <td style={{ padding: '12px 16px', color: 'var(--gray-700)' }}>
                        {fmtNum(run.total_records)}
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <span style={{ color: run.anomaly_count > 0 ? 'var(--red-700)' : 'var(--green-700)', fontWeight: 600 }}>
                          {fmtNum(run.anomaly_count)}
                        </span>
                      </td>
                      <td style={{ padding: '12px 16px', fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--gray-600)' }}>
                        {run.id}
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <span className={`ml-status-badge ${run.processing_status === 'completed' ? 'ml-status-normal' : run.processing_status === 'failed' ? 'ml-status-breached' : 'ml-status-at-risk'}`}>
                          {run.processing_status || 'completed'}
                        </span>
                      </td>
                      <td style={{ padding: '12px 16px', color: 'var(--gray-500)', fontSize: '11px' }}>
                        {formatDate(run.created_at)}
                      </td>
                      <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                        <button
                          type="button"
                          className={isCurrent ? 'primary-button' : 'secondary-button'}
                          style={{ padding: '4px 10px', fontSize: '11px' }}
                          onClick={() => handleSelectRun(run)}
                        >
                          {isCurrent ? 'Viewing Run' : 'Open Run'}
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
