/**
 * ClassifyPage.jsx
 * Upload + run classification. On success, switches to Reports tab.
 */
import React, { useRef, useState } from 'react'
import LoadingSpinner from '../components/LoadingSpinner.jsx'

const ALLOWED_EXTS = ['.pdf', '.docx', '.txt']
const API_BASE = '/api'

export default function ClassifyPage({ onResult }) {
  const inputRef = useRef(null)
  const [dragOver,      setDragOver]      = useState(false)
  const [selectedFile,  setSelectedFile]  = useState(null)
  const [fileError,     setFileError]     = useState('')
  const [loading,       setLoading]       = useState(false)
  const [apiError,      setApiError]      = useState('')

  function validateAndSet(file) {
    if (!file) return
    const ext = '.' + file.name.split('.').pop().toLowerCase()
    if (!ALLOWED_EXTS.includes(ext)) {
      setFileError(`Unsupported type "${ext}". Please upload PDF, DOCX, or TXT.`)
      setSelectedFile(null)
      return
    }
    setFileError('')
    setSelectedFile(file)
  }

  function handleDrop(e) {
    e.preventDefault()
    setDragOver(false)
    validateAndSet(e.dataTransfer.files[0])
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!selectedFile) return
    setLoading(true)
    setApiError('')

    const formData = new FormData()
    formData.append('file', selectedFile)
    const token = localStorage.getItem('cte_token')

    try {
      const res = await fetch(`${API_BASE}/classify`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      })
      if (res.status === 401) { window.location.reload(); return }
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }))
        throw new Error(err.detail || `HTTP ${res.status}`)
      }
      const data = await res.json()
      onResult(data, selectedFile)          // lift result up + switch to Reports tab
    } catch (err) {
      setApiError(`Classification failed: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="classify-page">
      <div className="page-header">
        <h1 className="page-title">📂 Classify Document</h1>
        <p className="page-subtitle">
          Upload a PDF, DOCX, or TXT file. The engine will extract text, score it
          against climate finance criteria, and route you to the Results report.
        </p>
      </div>

      <div className="classify-card">

        {/* Drop zone */}
        <div
          className={`drop-zone ${dragOver ? 'drag-over' : ''} ${selectedFile ? 'has-file' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.docx,.txt"
            style={{ display: 'none' }}
            onChange={(e) => validateAndSet(e.target.files[0])}
          />
          {selectedFile ? (
            <div className="drop-zone-selected">
              <span className="dz-file-icon">
                {selectedFile.name.endsWith('.pdf') ? '📄' :
                 selectedFile.name.endsWith('.docx') ? '📝' : '🔤'}
              </span>
              <div>
                <div className="dz-file-name">{selectedFile.name}</div>
                <div className="dz-file-size">
                  {(selectedFile.size / 1024).toFixed(1)} KB
                </div>
              </div>
              <button
                className="dz-clear-btn"
                onClick={(e) => { e.stopPropagation(); setSelectedFile(null) }}
                title="Remove file"
              >✕</button>
            </div>
          ) : (
            <div className="drop-zone-empty">
              <span className="dz-icon">☁️</span>
              <p className="dz-main">Drag &amp; drop your document here</p>
              <p className="dz-sub">or click to browse</p>
              <div className="dz-types">
                <span>PDF</span><span>DOCX</span><span>TXT</span>
              </div>
            </div>
          )}
        </div>

        {fileError && <div className="classify-error">{fileError}</div>}
        {apiError  && <div className="classify-error">{apiError}</div>}

        <button
          className="btn-classify"
          onClick={handleSubmit}
          disabled={!selectedFile || loading}
        >
          {loading ? <LoadingSpinner size="small" /> : null}
          {loading ? 'Classifying…' : '🚀 Run Classification'}
        </button>

        {loading && (
          <div className="classify-progress">
            <div className="classify-progress-bar" />
            <p>Extracting text, scoring keywords, running ClimateBERT…</p>
          </div>
        )}
      </div>

      {/* Info cards */}
      <div className="classify-info-row">
        <div className="classify-info-card">
          <div className="cic-icon">⚡</div>
          <div className="cic-title">Fast Extraction</div>
          <div className="cic-desc">Handles multi-page PDFs including scanned documents via OCR fallback.</div>
        </div>
        <div className="classify-info-card">
          <div className="cic-icon">🧠</div>
          <div className="cic-title">AI Scoring</div>
          <div className="cic-desc">Combines ClimateBERT embeddings, keyword analysis, and RAG similarity scoring.</div>
        </div>
        <div className="classify-info-card">
          <div className="cic-icon">📐</div>
          <div className="cic-title">RBI Aligned</div>
          <div className="cic-desc">Maps every document to an RBI BSR sector code for regulatory reporting.</div>
        </div>
      </div>
    </div>
  )
}
