/**
 * RagPage.jsx
 * Query the uploaded document via RAG (Retrieval-Augmented Generation).
 */
import React, { useState, useRef, useEffect } from 'react'

const API_BASE = '/api'

/** Convert classification result object into a readable text summary for RAG context */
function formatReportContext(r) {
  if (!r) return null
  const lines = [
    `=== CLASSIFICATION REPORT: ${r.filename ?? 'document'} ===`,
    `Classification: ${r.classification ?? 'N/A'}`,
    r.bsr_code              ? `BSR Code: ${r.bsr_code}` : null,
    r.mitigation_score      != null ? `Mitigation Score: ${parseFloat(r.mitigation_score).toFixed(4)}` : null,
    r.adaptation_score      != null ? `Adaptation Score: ${parseFloat(r.adaptation_score).toFixed(4)}` : null,
    r.kw_avg_mitigation_score != null ? `KW Mitigation Score: ${parseFloat(r.kw_avg_mitigation_score).toFixed(4)}` : null,
    r.kw_avg_adaptation_score != null ? `KW Adaptation Score: ${parseFloat(r.kw_avg_adaptation_score).toFixed(4)}` : null,
    r.avg_mitigation_similarity_score != null ? `Mitigation RAG Similarity: ${parseFloat(r.avg_mitigation_similarity_score).toFixed(4)}` : null,
    r.avg_adaptation_similarity_score != null ? `Adaptation RAG Similarity: ${parseFloat(r.avg_adaptation_similarity_score).toFixed(4)}` : null,
    r.avg_adaptation_action_score != null ? `Adaptation Action-to-Risk: ${parseFloat(r.avg_adaptation_action_score).toFixed(4)}` : null,
    r.sector_weights_raw    ? `Sector Weights: ${r.sector_weights_raw}` : null,
    r.district_vulnerabilities ? `Districts & Vulnerabilities: ${r.district_vulnerabilities}` : null,
    r.matched_keywords?.length ? `Matched Keywords: ${r.matched_keywords.join(', ')}` : null,
  ].filter(Boolean)
  return lines.join('\n')
}

const SUGGESTIONS = [
  'What is the primary climate objective of this project?',
  'Which districts are mentioned and what are their vulnerabilities?',
  'What sector does this project belong to?',
  'Does this project qualify for adaptation finance?',
  'What greenhouse gas reductions are targeted?',
]

export default function RagPage({ uploadedFile, result }) {
  const [query,    setQuery]    = useState('')
  const [messages, setMessages] = useState([])
  const [loading,  setLoading]  = useState(false)
  const [error,    setError]    = useState('')
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  async function handleAsk(q) {
    const text = (q || query).trim()
    if (!text) return
    setQuery('')
    setError('')
    setMessages((prev) => [...prev, { role: 'user', text }])
    setLoading(true)

    const token = localStorage.getItem('cte_token')
    try {
      const res = await fetch(`${API_BASE}/rag/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          query: text,
          report_context: formatReportContext(result) ?? undefined,
        }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }))
        throw new Error(err.detail || `HTTP ${res.status}`)
      }
      const data = await res.json()
      setMessages((prev) => [...prev, { role: 'assistant', text: data.answer }])
    } catch (err) {
      setError(`Query failed: ${err.message}`)
      setMessages((prev) => [...prev, { role: 'error', text: `Error: ${err.message}` }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="rag-page">
      <div className="page-header">
        <h1 className="page-title">🔍 RAG Query</h1>
        <p className="page-subtitle">
          Ask questions about the uploaded document. The engine retrieves the most
          relevant passages and generates a grounded answer.
          {uploadedFile && (
            <span className="rag-current-file"> &nbsp;📄 {uploadedFile.name}</span>
          )}
        </p>
        <div className="rag-context-pills">
          <span className={`rag-ctx-pill ${uploadedFile ? 'active' : 'inactive'}`}>
            📄 Document Index: {uploadedFile ? uploadedFile.name : 'None'}
          </span>
          <span className={`rag-ctx-pill ${result ? 'active' : 'inactive'}`}>
            📊 Report Data: {result ? result.classification : 'Not available'}
          </span>
        </div>
      </div>

      {/* Suggested questions */}
      {messages.length === 0 && (
        <div className="rag-suggestions">
          <div className="rag-sug-title">Try asking…</div>
          <div className="rag-sug-chips">
            {SUGGESTIONS.map((s) => (
              <button key={s} className="rag-sug-chip" onClick={() => handleAsk(s)}>
                {s}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Chat area */}
      <div className="rag-chat">
        {messages.map((m, i) => (
          <div key={i} className={`rag-msg rag-msg-${m.role}`}>
            <div className="rag-msg-avatar">
              {m.role === 'user' ? '🧑' : m.role === 'error' ? '⚠️' : '🤖'}
            </div>
            <div className="rag-msg-bubble">
              <pre className="rag-msg-text">{m.text}</pre>
            </div>
          </div>
        ))}
        {loading && (
          <div className="rag-msg rag-msg-assistant">
            <div className="rag-msg-avatar">🤖</div>
            <div className="rag-msg-bubble rag-typing">
              <span /><span /><span />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div className="rag-input-row">
        <input
          className="rag-input"
          type="text"
          placeholder="Ask a question about the document…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !loading && handleAsk()}
          disabled={loading}
        />
        <button
          className="rag-send-btn"
          onClick={() => handleAsk()}
          disabled={!query.trim() || loading}
        >
          {loading ? '…' : '➤'}
        </button>
      </div>
      {error && <div className="rag-error">{error}</div>}

      {messages.length > 0 && (
        <button className="btn-ghost" onClick={() => setMessages([])}>
          🗑 Clear conversation
        </button>
      )}
    </div>
  )
}
