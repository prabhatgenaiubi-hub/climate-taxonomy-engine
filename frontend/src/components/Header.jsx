/**
 * Header.jsx
 * Premium enterprise top navigation bar.
 */
import React, { useState, useRef, useEffect } from 'react'

export default function Header({ user, onLogout, onToggleSidebar }) {
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const dropRef = useRef(null)

  useEffect(() => {
    function onClickOutside(e) {
      if (dropRef.current && !dropRef.current.contains(e.target)) {
        setDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

  const initials = user
    ? (user.full_name || user.username)
        .split(' ').map((w) => w[0]).join('').toUpperCase().slice(0, 2)
    : '??'

  const timeGreeting = () => {
    const h = new Date().getHours()
    if (h < 12) return 'Good morning'
    if (h < 17) return 'Good afternoon'
    return 'Good evening'
  }

  return (
    <header className="nh-bar">
      {/* Animated gold accent line */}
      <div className="nh-accent" />

      <div className="nh-inner">

        {/* ── Hamburger (mobile / collapse) ── */}
        <button className="nh-hamburger" onClick={onToggleSidebar} aria-label="Toggle sidebar">
          <span /><span /><span />
        </button>

        {/* ── Platform identity ── */}
        <div className="nh-brand">
          <div className="nh-brand-icon">
            <img src="/Union_Bank_of_India_Logo.png" alt="Union Bank of India" className="nh-brand-logo" />
          </div>
          <div className="nh-brand-text">
            <span className="nh-brand-title">Climate Taxonomy Engine</span>
            <span className="nh-brand-sub">AI · Finance · Sustainability</span>
          </div>
        </div>

        {/* ── Right: badges + user ── */}
        <div className="nh-right">

          {/* Status pill */}
          <div className="nh-status-pill">
            <span className="nh-status-dot" />
            System Online
          </div>

          {/* Divider */}
          <div className="nh-divider" />

          {/* User section */}
          {user && (
            <div className="nh-user" ref={dropRef}>
              <div className="nh-user-meta">
                <span className="nh-user-greeting">{timeGreeting()}</span>
                <span className="nh-user-name">{user.full_name || user.username}</span>
              </div>

              <button
                className="nh-avatar-btn"
                onClick={() => setDropdownOpen((v) => !v)}
                aria-label="Open user menu"
              >
                <span className="nh-avatar">{initials}</span>
                <svg className="nh-caret" viewBox="0 0 10 6" fill="none">
                  <path d={dropdownOpen ? 'M1 5l4-4 4 4' : 'M1 1l4 4 4-4'}
                        stroke="currentColor" strokeWidth="1.5"
                        strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </button>

              {dropdownOpen && (
                <div className="nh-dropdown">
                  {/* Profile header */}
                  <div className="nh-dd-header">
                    <div className="nh-dd-avatar">{initials}</div>
                    <div className="nh-dd-info">
                      <div className="nh-dd-name">{user.full_name}</div>
                      <div className="nh-dd-email">{user.email || user.username}</div>
                      <span className="nh-dd-role">{user.role}</span>
                    </div>
                  </div>

                  <div className="nh-dd-divider" />

                  {/* Menu items */}
                  <div className="nh-dd-menu">
                    <button className="nh-dd-item" disabled>
                      <span className="nh-dd-item-icon">👤</span> Profile
                      <span className="nh-dd-item-badge">Soon</span>
                    </button>
                    <button className="nh-dd-item" disabled>
                      <span className="nh-dd-item-icon">⚙️</span> Settings
                      <span className="nh-dd-item-badge">Soon</span>
                    </button>
                  </div>

                  <div className="nh-dd-divider" />

                  <button
                    className="nh-dd-signout"
                    onClick={() => { setDropdownOpen(false); onLogout() }}
                  >
                    <svg viewBox="0 0 24 24" fill="none" width="16" height="16">
                      <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9"
                            stroke="currentColor" strokeWidth="2"
                            strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                    Sign Out
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
