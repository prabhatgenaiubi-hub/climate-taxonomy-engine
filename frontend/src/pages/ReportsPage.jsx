/**
 * ReportsPage.jsx
 * Shows full classification results and offers Excel / PDF / TXT downloads.
 */
import React, { useState } from 'react'

const COLORS = {
  'Mitigation':                '#1a7a4a',
  'Adaptation':                '#1565c0',
  'Mitigation and Adaptation': '#6a1b9a',
  'Not under Climate Finance': '#b71c1c',
}

function Badge({ label }) {
  return (
    <span className="rpt-badge" style={{ background: COLORS[label] || '#555' }}>
      {label}
    </span>
  )
}

function ScoreBar({ label, value, max = 5 }) {
  const pct = Math.min(100, (parseFloat(value) / max) * 100)
  return (
    <div className="score-row">
      <span className="score-label">{label}</span>
      <div className="score-bar-track">
        <div className="score-bar-fill" style={{ width: `${pct}%` }} />
      </div>
      <span className="score-value">{parseFloat(value).toFixed(3)}</span>
    </div>
  )
}

// ── Download helpers ──────────────────────────────────────────────────────────

function downloadTxt(result) {
  const lines = Object.entries(result)
    .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
    .join('\n')
  const blob = new Blob([lines], { type: 'text/plain' })
  trigger(blob, `${baseName(result)}_classification.txt`)
}

function downloadCsv(result) {
  const keys   = Object.keys(result)
  const values = Object.values(result).map((v) =>
    Array.isArray(v) ? `"${v.join('; ')}"` : `"${v ?? ''}"`
  )
  const csv = `${keys.join(',')}\n${values.join(',')}`
  const blob = new Blob([csv], { type: 'text/csv' })
  trigger(blob, `${baseName(result)}_classification.csv`)
}

function downloadExcel(result) {
  // Build a minimal XLSX-compatible XML (SpreadsheetML)
  const rows = Object.entries(result).map(([k, v]) => {
    const val = Array.isArray(v) ? v.join('; ') : (v ?? '')
    return `<Row><Cell><Data ss:Type="String">${escXml(k)}</Data></Cell>` +
           `<Cell><Data ss:Type="String">${escXml(String(val))}</Data></Cell></Row>`
  })
  const xml = `<?xml version="1.0"?><Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"` +
    ` xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">` +
    `<Worksheet ss:Name="Classification"><Table>${rows.join('')}</Table></Worksheet></Workbook>`
  const blob = new Blob([xml], { type: 'application/vnd.ms-excel' })
  trigger(blob, `${baseName(result)}_classification.xls`)
}

function downloadPdf(result) {
  // Build a simple HTML page and use browser print to PDF
  const rows = Object.entries(result)
    .map(([k, v]) => {
      const val = Array.isArray(v) ? v.join(', ') : (v ?? '')
      return `<tr><td style="padding:8px 12px;border:1px solid #ddd;font-weight:600;background:#f5f5f5">${k}</td>` +
             `<td style="padding:8px 12px;border:1px solid #ddd">${val}</td></tr>`
    })
    .join('')
  const html = `<html><head><title>Classification Report</title>
    <style>body{font-family:Arial;padding:32px}h1{color:#003087}table{width:100%;border-collapse:collapse}</style>
    </head><body>
    <h1>Climate Taxonomy Engine — Classification Report</h1>
    <p>Generated: ${new Date().toLocaleString()}</p>
    <table>${rows}</table>
    </body></html>`
  const blob = new Blob([html], { type: 'text/html' })
  const url  = URL.createObjectURL(blob)
  const win  = window.open(url, '_blank')
  if (win) {
    win.onload = () => { win.print(); URL.revokeObjectURL(url) }
  }
}

function baseName(result) {
  return result.filename?.replace(/\.[^.]+$/, '') ?? 'result'
}
function trigger(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a   = Object.assign(document.createElement('a'), { href: url, download: filename })
  a.click()
  URL.revokeObjectURL(url)
}
function escXml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function ReportsPage({ result, onGoClassify }) {
  const [showDetail, setShowDetail] = useState(false)

  if (!result) {
    return (
      <div className="reports-empty">
        <div className="reports-empty-icon">📋</div>
        <h2>No Report Yet</h2>
        <p>Run a classification first to see results here.</p>
        <button className="btn-primary" onClick={onGoClassify}>
          ➜ Go to Classify
        </button>
      </div>
    )
  }

  return (
    <div className="reports-page">
      <div className="page-header">
        <h1 className="page-title">📊 Classification Report</h1>
        <p className="page-subtitle">
          Results for <strong>{result.filename}</strong>
        </p>
      </div>

      {/* ── Summary card ── */}
      <div className="rpt-summary-card">
        <div className="rpt-summary-left">
          <div className="rpt-summary-label">Final Classification</div>
          <Badge label={result.classification} />
          {result.bsr_code && (
            <div className="rpt-bsr">BSR Code: <strong>{result.bsr_code}</strong></div>
          )}
        </div>
        <div className="rpt-summary-scores">
          <div className="rpt-score-item">
            <span className="rpt-score-val">{parseFloat(result.mitigation_score).toFixed(3)}</span>
            <span className="rpt-score-key">Mitigation Score</span>
          </div>
          <div className="rpt-score-divider" />
          <div className="rpt-score-item">
            <span className="rpt-score-val">{parseFloat(result.adaptation_score).toFixed(3)}</span>
            <span className="rpt-score-key">Adaptation Score</span>
          </div>
        </div>
      </div>

      {/* ── Detailed scores ── */}
      <button className="btn-secondary" onClick={() => setShowDetail((v) => !v)}>
        {showDetail ? '▲ Hide Detailed Scores' : '▼ Show Detailed Scores'}
      </button>
      {showDetail && (
        <div className="detail-card">
          {[
            ['kw_avg_mitigation_score',        'KW Mitigation Score'],
            ['kw_avg_adaptation_score',         'KW Adaptation Score'],
            ['avg_mitigation_similarity_score', 'Mitigation RAG Similarity'],
            ['avg_adaptation_similarity_score', 'Adaptation RAG Similarity'],
            ['avg_adaptation_action_score',     'Adaptation Action-to-Risk'],
          ].map(([key, label]) =>
            result[key] != null ? <ScoreBar key={key} label={label} value={result[key]} /> : null
          )}
        </div>
      )}

      {/* ── Extra info ── */}
      {result.sector_weights_raw && (
        <div className="info-card">
          <strong>Sector Weights:</strong>
          <p>{result.sector_weights_raw}</p>
        </div>
      )}
      {result.district_vulnerabilities && (
        <div className="info-card">
          <strong>Districts &amp; Vulnerabilities:</strong>
          <p>{result.district_vulnerabilities}</p>
        </div>
      )}
      {result.matched_keywords?.length > 0 && (
        <div className="info-card">
          <strong>Matched Keywords:</strong>
          <div className="keyword-chips">
            {result.matched_keywords.map((kw, i) => (
              <span key={i} className="keyword-chip">{kw}</span>
            ))}
          </div>
        </div>
      )}

      {/* ── Download buttons ── */}
      <div className="rpt-download-section">
        <div className="rpt-download-title">⬇ Download Report</div>
        <div className="rpt-download-btns">
          <button className="dl-btn dl-pdf" onClick={() => downloadPdf(result)}>
            <span className="dl-icon">📄</span>
            <span>PDF (Print)</span>
          </button>
          <button className="dl-btn dl-csv" onClick={() => downloadCsv(result)}>
            <span className="dl-icon">🗒️</span>
            <span>CSV</span>
          </button>
          <button className="dl-btn dl-txt" onClick={() => downloadTxt(result)}>
            <span className="dl-icon">🔤</span>
            <span>TXT</span>
          </button>
        </div>
      </div>
    </div>
  )
}
