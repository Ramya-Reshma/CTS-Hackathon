import React, { useState } from 'react'
import { useStore } from '../hooks/useStore'
import { uploadAndAnalyze } from '../services/api'
import './Upload.css'

const PROCESSING_STAGES = [
  'File uploaded',
  'Running anomaly detection',
  'Running RCA / RAG analysis',
  'Saving anomaly results',
  'Analysis complete',
]

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

  const handleDragEnter = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(true)
  }

  const handleDragLeave = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
  }

  const handleDragOver = (e) => {
    e.preventDefault()
    e.stopPropagation()
  }

  const handleDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    const files = e.dataTransfer.files
    if (files && files.length > 0) {
      handleFileSelect(files[0])
    }
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
    if (e.target.files && e.target.files.length > 0) {
      handleFileSelect(e.target.files[0])
    }
  }

  const handleAnalyze = async () => {
    if (!selectedFile) {
      setError('Please select a file')
      return
    }

    setIsUploading(true)
    setError(null)
    setProcessingStage(0)

    try {
      // Simulate stage progression
      const stageInterval = setInterval(() => {
        setProcessingStage(prev => {
          if (prev < PROCESSING_STAGES.length - 1) {
            return prev + 1
          }
          clearInterval(stageInterval)
          return prev
        })
      }, 1000)

      const result = await uploadAndAnalyze(selectedFile)

      clearInterval(stageInterval)
      setProcessingStage(PROCESSING_STAGES.length - 1)

      // Store run info
      setCurrentRun(result)

      // Store statistics
      setStatistics({
        totalRecords: result.total_records,
        totalAnomalies: result.total_anomalies,
        bySeverity: result.severity_summary,
      })

      // Reset form
      setSelectedFile(null)
    } catch (err) {
      setError(err.message || 'Analysis failed. Please check the backend logs.')
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <div className="upload-container">
      <div className="upload-header">
        <h1>UC10</h1>
        <p className="subtitle">Claims & Authorization Anomaly Monitor</p>
      </div>

      <div className="upload-content">
        {!isUploading ? (
          <>
            <div className="upload-section">
              <h2>Upload Claims Data</h2>
              <p className="upload-description">
                Upload a CSV or Excel file containing claims data to begin anomaly detection analysis.
              </p>

              <div
                className={`upload-dropzone ${dragActive ? 'active' : ''}`}
                onDragEnter={handleDragEnter}
                onDragLeave={handleDragLeave}
                onDragOver={handleDragOver}
                onDrop={handleDrop}
              >
                <div className="dropzone-content">
                  <div className="upload-icon">📁</div>
                  <h3>Drag and drop your file here</h3>
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
                  <p className="file-info">Supported formats: CSV, XLS, XLSX (Max 100MB)</p>
                </div>
              </div>

              {selectedFile && (
                <div className="file-selected">
                  <div className="file-info-box">
                    <div className="file-icon">📄</div>
                    <div className="file-details">
                      <p className="file-name">{selectedFile.name}</p>
                      <p className="file-size">{(selectedFile.size / 1024 / 1024).toFixed(2)} MB</p>
                    </div>
                  </div>
                  <button
                    className="analyze-button"
                    onClick={handleAnalyze}
                    disabled={isUploading}
                  >
                    {isUploading ? 'Analyzing...' : 'Start Analysis'}
                  </button>
                </div>
              )}

              {error && (
                <div className="error-message">
                  <span className="error-icon">⚠️</span>
                  {error}
                </div>
              )}
            </div>

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
            <h2>Analyzing Claims Data</h2>
            <p className="processing-subtitle">Please wait while we process your file...</p>

            <div className="processing-stages">
              {PROCESSING_STAGES.map((stage, index) => (
                <div
                  key={index}
                  className={`stage ${
                    index <= processingStage ? 'completed' : 'pending'
                  }`}
                >
                  <div className="stage-indicator">
                    {index < processingStage ? (
                      <span className="checkmark">✓</span>
                    ) : index === processingStage ? (
                      <div className="spinner-small"></div>
                    ) : (
                      <span className="number">{index + 1}</span>
                    )}
                  </div>
                  <span className="stage-name">{stage}</span>
                </div>
              ))}
            </div>

            <p className="processing-note">
              This may take a few minutes depending on file size...
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
