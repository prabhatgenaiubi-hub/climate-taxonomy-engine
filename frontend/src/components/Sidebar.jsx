/**
 * Sidebar.jsx
 * Premium collapsible left navigation panel.
 */
import React, { useState } from 'react'
import NavItem from './NavItem.jsx'

const NAV_ITEMS = [
  {
    id: 'home',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" width="18" height="18">
        <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"
              stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        <polyline points="9 22 9 12 15 12 15 22"
                  stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    ),
    label: 'Home',
    desc:  'Overview & features',
  },
  {
    id: 'classify',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" width="18" height="18">
        <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"
              stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        <polyline points="14 2 14 8 20 8"
                  stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        <line x1="16" y1="13" x2="8" y2="13"
              stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
        <line x1="16" y1="17" x2="8" y2="17"
              stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
        <polyline points="10 9 9 9 8 9"
                  stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    ),
    label: 'Classify',
    desc:  'Upload & analyse',
  },
  {
    id: 'reports',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" width="18" height="18">
        <line x1="18" y1="20" x2="18" y2="10" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
        <line x1="12" y1="20" x2="12" y2="4"  stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
        <line x1="6"  y1="20" x2="6"  y2="14" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
      </svg>
    ),
    label: 'Reports',
    desc:  'Results & exports',
  },
  {
    id: 'rag',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" width="18" height="18">
        <circle cx="11" cy="11" r="8" stroke="currentColor" strokeWidth="2"/>
        <line x1="21" y1="21" x2="16.65" y2="16.65"
              stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
      </svg>
    ),
    label: 'RAG Query',
    desc:  'Ask the document',
  },
]

export default function Sidebar({ activeTab, onTabChange, hasResult, collapsed, onToggleCollapse }) {
  return (
    <aside className={`sb ${collapsed ? 'sb--collapsed' : ''}`}>

      {/* ── Logo / branding strip ── */}
      <div className="sb-header">
        <div className="sb-logo-fallback">
          <img src="/Union_bank_small_icon.png" alt="UBI" className="sb-logo-img" />
        </div>
        {!collapsed && (
          <div className="sb-brand-text">
            <span className="sb-brand-title">Climate Taxonomy Engine</span>
            <span className="sb-brand-sub">AI · Finance · Sustainability</span>
          </div>
        )}
        <button className="sb-collapse-btn" onClick={onToggleCollapse} title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}>
          <svg viewBox="0 0 24 24" fill="none" width="16" height="16">
            <path d={collapsed ? 'M9 18l6-6-6-6' : 'M15 18l-6-6 6-6'}
                  stroke="currentColor" strokeWidth="2"
                  strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
      </div>

      {/* ── Section label ── */}
      {!collapsed && <div className="sb-section-label">NAVIGATION</div>}

      {/* ── Nav items ── */}
      <nav className="sb-nav">
        {NAV_ITEMS.map((item) => (
          <NavItem
            key={item.id}
            icon={item.icon}
            label={item.label}
            desc={!collapsed ? item.desc : undefined}
            active={activeTab === item.id}
            disabled={item.id === 'reports' && !hasResult}
            badge={item.id === 'reports' && hasResult ? '●' : undefined}
            onClick={() => onTabChange(item.id)}
          />
        ))}
      </nav>

      {/* ── Spacer ── */}
      <div style={{ flex: 1 }} />

      {/* ── Bottom help card (only when expanded) ── */}
      {!collapsed && (
        <div className="sb-help-card">
          <div className="sb-help-icon">💡</div>
          <div className="sb-help-text">
            <div className="sb-help-title">Need help?</div>
            <div className="sb-help-desc">Check the docs or contact support.</div>
          </div>
        </div>
      )}

      {/* ── Footer ── */}
      <div className="sb-footer">
        {collapsed ? (
          <span title="ClimateBERT v1.0">⚡</span>
        ) : (
          <>
            <span className="sb-footer-text">ClimateBERT + RAG</span>
            <span className="sb-footer-ver">v1.0</span>
          </>
        )}
      </div>
    </aside>
  )
}
