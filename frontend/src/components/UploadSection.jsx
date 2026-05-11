/**
 * UploadSection.jsx
 * Drag-and-drop + click-to-upload file uploader.
 */
import React, { useRef, useState } from 'react'

const ALLOWED_TYPES = ['.pdf', '.docx', '.txt']

export default function UploadSection({ onUpload, loading }) {
  const inputRef = useRef(null)
  const [dragOver, setDragOver] = useState(false)
  const [selectedFile, setSelectedFile] = useState(null)
  const [error, setError] = useState('')

  function validateAndSet(file) {
    if (!file) return
    const ext = '.' + file.name.split('.').pop().toLowerCase()
    if (!ALLOWED_TYPES.includes(ext)) {
      setError(`Unsupported file type "${ext}". Please upload PDF, DOCX, or TXT.`)
      setSelectedFile(null)
      return
    }
    setError('')
    setSelectedFile(file)
  }

  function handleDrop(e) {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    validateAndSet(file)
  }

  function handleFileChange(e) {
    validateAndSet(e.target.files[0])
  }

  function handleSubmit(e) {
    e.preventDefault()
    if (selectedFile) onUpload(selectedFile)
  }

  return (
    <section className="upload-section">
      <h2 className="section-title">📂 Upload Document</h2>

      <div
        className={`drop-zone ${dragOver ? 'drag-over' : ''} ${selectedFile ? 'has-file' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && inputRef.current?.click()}
        aria-label="Upload file drop zone"
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx,.txt"
          style={{ display: 'none' }}
          onChange={handleFileChange}
        />
        {selectedFile ? (
          <div className="drop-zone-file-info">
            <span className="file-icon">📄</span>
            <span className="file-name">{selectedFile.name}</span>
            <span className="file-size">
              ({(selectedFile.size / 1024).toFixed(1)} KB)
            </span>
          </div>
        ) : (
          <div className="drop-zone-placeholder">
            <span className="drop-icon">⬆️</span>
            <p>Drag &amp; drop your file here, or <strong>click to browse</strong></p>
            <p className="drop-hint">PDF · DOCX · TXT</p>
          </div>
        )}
      </div>

      {error && <p className="upload-error">{error}</p>}

      <button
        className="btn-primary classify-btn"
        onClick={handleSubmit}
        disabled={!selectedFile || loading}
      >
        {loading ? '⏳ Classifying…' : '🔍 Classify Document'}
      </button>
    </section>
  )
}
