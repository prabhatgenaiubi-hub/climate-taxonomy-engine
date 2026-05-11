/**
 * NavItem.jsx
 * Reusable sidebar navigation item.
 */
import React from 'react'

export default function NavItem({ icon, label, desc, active, disabled, badge, onClick }) {
  return (
    <button
      className={`nav-item ${active ? 'nav-item--active' : ''} ${disabled ? 'nav-item--disabled' : ''}`}
      onClick={disabled ? undefined : onClick}
      title={disabled ? 'Coming soon' : label}
      aria-current={active ? 'page' : undefined}
    >
      {/* Left accent bar (shown when active) */}
      <span className="nav-item__accent" />

      {/* Icon */}
      <span className="nav-item__icon">{icon}</span>

      {/* Text */}
      <span className="nav-item__text">
        <span className="nav-item__label">{label}</span>
        {desc && <span className="nav-item__desc">{desc}</span>}
      </span>

      {/* Badge (e.g. "New", green dot, count) */}
      {badge && <span className="nav-item__badge">{badge}</span>}
    </button>
  )
}
