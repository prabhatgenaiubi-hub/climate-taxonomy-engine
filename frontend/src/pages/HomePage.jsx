/**
 * HomePage.jsx
 * Welcome screen — user greeting, app description, feature overview.
 */
import React from 'react'

const FEATURES = [
  {
    icon: '🌱',
    title: 'Mitigation Classification',
    desc: 'Identifies documents aligned with greenhouse gas reduction activities using keyword scoring, sector weights, and ClimateBERT embeddings.',
  },
  {
    icon: '🛡️',
    title: 'Adaptation Classification',
    desc: 'Detects climate risk adaptation actions linked to district-level vulnerability data and MDB/IDFC framework benchmarks.',
  },
  {
    icon: '🗺️',
    title: 'BSR Code Mapping',
    desc: 'Automatically maps projects to RBI Business Sector Report codes for regulatory compliance and reporting.',
  },
  {
    icon: '🔍',
    title: 'RAG-Powered Query',
    desc: 'Ask questions about any uploaded document using Retrieval-Augmented Generation backed by a FAISS vector index.',
  },
  {
    icon: '📊',
    title: 'Detailed Scoring',
    desc: 'Multi-dimensional scores: keyword similarity, RAG cosine similarity, adaptation action-to-risk alignment, and sector weights.',
  },
  {
    icon: '⬇️',
    title: 'Export Results',
    desc: 'Download classification reports in Excel, PDF, or TXT formats for audit trails and portfolio reporting.',
  },
]

const PIPELINE_STEPS = [
  { step: '01', label: 'Text Extraction',       desc: 'Parses PDF, DOCX, or TXT files and cleans raw text.' },
  { step: '02', label: 'Sector Filtering',       desc: 'Identifies BSR code and sector weights from content.' },
  { step: '03', label: 'Vulnerability Check',    desc: 'Matches districts to climate vulnerability index.' },
  { step: '04', label: 'Climate Classification', desc: 'Scores mitigation & adaptation using ClimateBERT + RAG.' },
  { step: '05', label: 'Report Generation',      desc: 'Produces structured results ready for export.' },
]

export default function HomePage({ user }) {
  const greeting = () => {
    const h = new Date().getHours()
    if (h < 12) return 'Good Morning'
    if (h < 17) return 'Good Afternoon'
    return 'Good Evening'
  }

  return (
    <div className="home-page">

      {/* ── Hero banner ── */}
      <div className="home-hero">
        <div className="home-hero-text">
          <div className="home-greeting">
            {greeting()}, <strong>{user?.full_name || user?.username}</strong> 👋
          </div>
          <h1 className="home-title">Climate Taxonomy Engine</h1>
          <p className="home-subtitle">
            An AI-powered document classification platform for Union Bank of India —
            built to identify and score climate finance eligibility in line with RBI,
            MDB/IDFC, and EU Taxonomy frameworks.
          </p>
          <div className="home-hero-tags">
            <span className="hero-tag">🏦 Union Bank of India</span>
            <span className="hero-tag">🤖 ClimateBERT</span>
            <span className="hero-tag">📐 RBI BSR Codes</span>
            <span className="hero-tag">🌍 MDB/IDFC Aligned</span>
          </div>
        </div>
        <div className="home-hero-badge">
          <div className="hero-stat">
            <span className="hero-stat-num">4</span>
            <span className="hero-stat-label">Classification<br/>Categories</span>
          </div>
          <div className="hero-stat">
            <span className="hero-stat-num">5</span>
            <span className="hero-stat-label">Pipeline<br/>Stages</span>
          </div>
          <div className="hero-stat">
            <span className="hero-stat-num">3</span>
            <span className="hero-stat-label">Export<br/>Formats</span>
          </div>
        </div>
      </div>

      {/* ── Features grid ── */}
      <h2 className="home-section-title">Platform Capabilities</h2>
      <div className="home-features-grid">
        {FEATURES.map((f) => (
          <div className="home-feature-card" key={f.title}>
            <span className="feature-icon">{f.icon}</span>
            <div>
              <div className="feature-title">{f.title}</div>
              <div className="feature-desc">{f.desc}</div>
            </div>
          </div>
        ))}
      </div>

      {/* ── Pipeline ── */}
      <h2 className="home-section-title">How It Works</h2>
      <div className="home-pipeline">
        {PIPELINE_STEPS.map((s, i) => (
          <React.Fragment key={s.step}>
            <div className="pipeline-step">
              <div className="pipeline-num">{s.step}</div>
              <div className="pipeline-label">{s.label}</div>
              <div className="pipeline-desc">{s.desc}</div>
            </div>
            {i < PIPELINE_STEPS.length - 1 && <div className="pipeline-arrow">›</div>}
          </React.Fragment>
        ))}
      </div>

      {/* ── Classification categories ── */}
      <h2 className="home-section-title">Classification Categories</h2>
      <div className="home-categories">
        {[
          { label: 'Mitigation',                  color: '#1a7a4a', bg: '#e8f5e9', desc: 'Reducing greenhouse gas emissions.' },
          { label: 'Adaptation',                  color: '#1565c0', bg: '#e3f2fd', desc: 'Adapting to climate change impacts.' },
          { label: 'Mitigation and Adaptation',   color: '#6a1b9a', bg: '#f3e5f5', desc: 'Both mitigation and adaptation.' },
          { label: 'Not under Climate Finance',   color: '#b71c1c', bg: '#ffebee', desc: 'Not qualifying for climate finance.' },
        ].map((c) => (
          <div className="category-card" key={c.label} style={{ borderLeft: `4px solid ${c.color}`, background: c.bg }}>
            <span className="category-badge" style={{ background: c.color }}>{c.label}</span>
            <span className="category-desc">{c.desc}</span>
          </div>
        ))}
      </div>

    </div>
  )
}
