/**
 * ResultCard.jsx
 * Displays full classification results for one document.
 */
import React, { useState } from 'react'

const CLASSIFICATION_COLORS = {
  'Mitigation':                  '#1a7a4a',
  'Adaptation':                  '#1565c0',
  'Mitigation and Adaptation':   '#6a1b9a',
  'Not under Climate Finance':   '#b71c1c',
}

function Badge({ label }) {
  const color = CLASSIFICATION_COLORS[label] || '#555'
  return (
    <span className="badge" style={{ backgroundColor: color }}>
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

export default function ResultCard({ result, onDownload }) {
  const [showDetail, setShowDetail] = useState(false)

  return (
    <section className="result-section">
      <h2 className="section-title">📊 Classification Results</h2>

      {/* Main summary card */}
      <div className="result-card">
        <div className="result-row">
          <span className="result-key">File</span>
          <span className="result-val">{result.filename}</span>
        </div>
        <div className="result-row">
          <span className="result-key">Classification</span>
          <span className="result-val">
            <Badge label={result.classification} />
          </span>
        </div>
        <div className="result-row">
          <span className="result-key">BSR Code</span>
          <span className="result-val">{result.bsr_code ?? 'N/A'}</span>
        </div>
        <div className="result-row">
          <span className="result-key">Mitigation Score</span>
          <span className="result-val">{parseFloat(result.mitigation_score).toFixed(3)}</span>
        </div>
        <div className="result-row">
          <span className="result-key">Adaptation Score</span>
          <span className="result-val">{parseFloat(result.adaptation_score).toFixed(3)}</span>
        </div>
        {result.sector_mit_weight != null && (
          <div className="result-row">
            <span className="result-key">Mitigation Sector Weight</span>
            <span className="result-val">{result.sector_mit_weight}</span>
          </div>
        )}
        {result.sector_adapt_weight != null && (
          <div className="result-row">
            <span className="result-key">Adaptation Sector Weight</span>
            <span className="result-val">{result.sector_adapt_weight}</span>
          </div>
        )}
      </div>

      {/* Detailed scores accordion */}
      <button
        className="btn-secondary"
        onClick={() => setShowDetail((v) => !v)}
      >
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
            result[key] != null ? (
              <ScoreBar key={key} label={label} value={result[key]} />
            ) : null
          )}
        </div>
      )}

      {/* Sector weights */}
      {result.sector_weights_raw && (
        <div className="info-card">
          <strong>Sector Weights:</strong>
          <p>{result.sector_weights_raw}</p>
        </div>
      )}

      {/* District vulnerabilities */}
      {result.district_vulnerabilities && (
        <div className="info-card">
          <strong>Districts &amp; Vulnerabilities:</strong>
          <p>{result.district_vulnerabilities}</p>
        </div>
      )}

      {/* Matched keywords */}
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

      {/* Download */}
      <button className="btn-primary download-btn" onClick={onDownload}>
        ⬇ Download Results as CSV
      </button>
    </section>
  )
}
