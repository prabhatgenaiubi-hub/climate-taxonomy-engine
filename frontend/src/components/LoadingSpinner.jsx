/**
 * LoadingSpinner.jsx
 * Animated progress indicator shown during classification.
 */
import React, { useEffect, useState } from 'react'

const STEPS = [
  { label: 'Extracting text…',         pct: 20 },
  { label: 'Running sector filter…',   pct: 40 },
  { label: 'Checking vulnerabilities…',pct: 65 },
  { label: 'Classifying document…',    pct: 85 },
  { label: 'Finalising results…',      pct: 95 },
]

export default function LoadingSpinner() {
  const [step, setStep] = useState(0)

  useEffect(() => {
    if (step >= STEPS.length - 1) return
    const t = setTimeout(() => setStep((s) => s + 1), 2200)
    return () => clearTimeout(t)
  }, [step])

  const current = STEPS[step]

  return (
    <div className="loading-overlay" role="status" aria-live="polite">
      <div className="loading-card">
        <div className="spinner" aria-hidden="true" />
        <p className="loading-step">{current.label}</p>
        <div className="progress-bar-track">
          <div
            className="progress-bar-fill"
            style={{ width: `${current.pct}%` }}
          />
        </div>
        <p className="progress-pct">{current.pct}%</p>
      </div>
    </div>
  )
}
