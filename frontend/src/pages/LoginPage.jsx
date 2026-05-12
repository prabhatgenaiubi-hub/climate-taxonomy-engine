/**
 * frontend/src/pages/LoginPage.jsx
 * Two-column login page:
 *   LEFT  — branding (logo, app name, description)
 *   RIGHT — Sign In / Register form
 */
import React, { useState } from 'react'

export default function LoginPage({ onLoginSuccess }) {
  const [tab,     setTab]     = useState('login')
  const [form,    setForm]    = useState({ username: '', password: '', confirmPassword: '', email: '', full_name: '' })
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState('')
  const [success, setSuccess] = useState('')

  function handleChange(e) {
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }))
  }

  async function handleLogin(e) {
    e.preventDefault()
    setError(''); setSuccess(''); setLoading(true)
    try {
      const body = new URLSearchParams()
      body.append('username', form.username)
      body.append('password', form.password)
      const res  = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body,
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Login failed')
      localStorage.setItem('cte_token', data.access_token)
      localStorage.setItem('cte_user',  JSON.stringify(data.user))
      onLoginSuccess(data.user)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleRegister(e) {
    e.preventDefault()
    setError(''); setSuccess('')
    if (form.password !== form.confirmPassword) {
      setError('Passwords do not match.')
      return
    }
    setLoading(true)
    try {
      const res  = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username:  form.username,
          password:  form.password,
          email:     form.email,
          full_name: form.full_name,
        }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Registration failed')
      setSuccess('Account created! You can now sign in.')
      setTab('login')
      setForm((f) => ({ ...f, password: '', confirmPassword: '', email: '', full_name: '' }))
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-split-card">

        {/* ── LEFT PANEL — Branding ─────────────────────────── */}
        <div className="login-left">
          <div className="login-left-inner">
            <img
              src="/Union_Bank_of_India_Logo.png"
              alt="Union Bank of India"
              className="login-brand-logo"
              onError={(e) => { e.target.style.display = 'none' }}
            />
            <h1 className="login-brand-title">Climate Taxonomy Engine</h1>
            <p className="login-brand-subtitle">Union Bank of India</p>
            <div className="login-divider" />
            <p className="login-brand-desc">
              An intelligent platform to classify financial documents for
              climate finance eligibility — powered by ClimateBERT and
              Retrieval-Augmented Generation (RAG).
            </p>
            <ul className="login-feature-list">
              <li>🌿 Mitigation &amp; Adaptation classification</li>
              <li>📄 PDF, DOCX and TXT support</li>
              <li>🗺️ District-level vulnerability mapping</li>
              <li>📊 RBI sector-weight scoring</li>
              <li>⬇️ Exportable CSV reports</li>
            </ul>
          </div>
          <p className="login-brand-footer">
            © {new Date().getFullYear()} Union Bank of India. All rights reserved.
          </p>
        </div>

        {/* ── RIGHT PANEL — Auth Form ───────────────────────── */}
        <div className="login-right">
          <div className="login-right-inner">

            <h2 className="login-form-title">
              {tab === 'login' ? 'Welcome back' : 'Create account'}
            </h2>
            <p className="login-form-subtitle">
              {tab === 'login'
                ? 'Sign in to your account to continue'
                : 'Register to access the platform'}
            </p>

            {/* Tabs */}
            <div className="login-tabs">
              <button
                className={`login-tab ${tab === 'login' ? 'active' : ''}`}
                onClick={() => { setTab('login'); setError(''); setSuccess('') }}
              >
                Sign In
              </button>
              <button
                className={`login-tab ${tab === 'register' ? 'active' : ''}`}
                onClick={() => { setTab('register'); setError(''); setSuccess('') }}
              >
                Register
              </button>
            </div>

            {/* Messages */}
            {error   && <div className="login-error"   role="alert">⚠️ {error}</div>}
            {success && <div className="login-success" role="status">✅ {success}</div>}

            {/* ── Sign In Form ── */}
            {tab === 'login' && (
              <form className="login-form" onSubmit={handleLogin}>
                <div className="form-group">
                  <label htmlFor="username">Username</label>
                  <input
                    id="username" name="username" type="text"
                    placeholder="Enter your username"
                    value={form.username} onChange={handleChange}
                    required autoFocus
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="password">Password</label>
                  <input
                    id="password" name="password" type="password"
                    placeholder="Enter your password"
                    value={form.password} onChange={handleChange}
                    required
                  />
                </div>
                <button className="btn-primary login-btn" type="submit" disabled={loading}>
                  {loading ? '⏳ Signing in…' : 'Sign In →'}
                </button>
              </form>
            )}

            {/* ── Register Form ── */}
            {tab === 'register' && (
              <form className="login-form" onSubmit={handleRegister}>
                <div className="form-group">
                  <label htmlFor="full_name">Full Name</label>
                  <input
                    id="full_name" name="full_name" type="text"
                    placeholder="Your full name"
                    value={form.full_name} onChange={handleChange}
                    required autoFocus
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="email">Email</label>
                  <input
                    id="email" name="email" type="email"
                    placeholder="your.email@unionbank.com"
                    value={form.email} onChange={handleChange}
                    required
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="reg_username">Username</label>
                  <input
                    id="reg_username" name="username" type="text"
                    placeholder="Choose a username"
                    value={form.username} onChange={handleChange}
                    required
                  />
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label htmlFor="reg_password">Password</label>
                    <input
                      id="reg_password" name="password" type="password"
                      placeholder="Choose a password"
                      value={form.password} onChange={handleChange}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label htmlFor="confirmPassword">Re-enter Password</label>
                    <input
                      id="confirmPassword" name="confirmPassword" type="password"
                      placeholder="Confirm password"
                      value={form.confirmPassword} onChange={handleChange}
                      required
                    />
                  </div>
                </div>
                <button className="btn-primary login-btn" type="submit" disabled={loading}>
                  {loading ? '⏳ Creating account…' : 'Create Account →'}
                </button>
              </form>
            )}

          </div>
        </div>

      </div>
    </div>
  )
}
