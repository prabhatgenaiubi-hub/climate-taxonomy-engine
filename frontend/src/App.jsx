/**
 * App.jsx
 * Root component — auth gate + left-sidebar tab navigation.
 */
import React, { useState, useEffect } from 'react'
import Header  from './components/Header.jsx'
import Sidebar from './components/Sidebar.jsx'
import LoginPage    from './pages/LoginPage.jsx'
import HomePage     from './pages/HomePage.jsx'
import ClassifyPage from './pages/ClassifyPage.jsx'
import ReportsPage  from './pages/ReportsPage.jsx'
import RagPage      from './pages/RagPage.jsx'

export default function App() {
  const [user,         setUser]         = useState(null)
  const [activeTab,    setActiveTab]    = useState('home')
  const [result,       setResult]       = useState(null)
  const [uploadedFile, setUploadedFile] = useState(null)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  useEffect(() => {
    const token = localStorage.getItem('cte_token')
    const saved = localStorage.getItem('cte_user')
    if (token && saved) {
      try { setUser(JSON.parse(saved)) } catch { /* ignore */ }
    }
  }, [])

  function handleLoginSuccess(userObj) { setUser(userObj) }

  function handleLogout() {
    localStorage.removeItem('cte_token')
    localStorage.removeItem('cte_user')
    setUser(null)
    setResult(null)
    setUploadedFile(null)
    setActiveTab('home')
  }

  function handleResult(data, file) {
    setResult(data)
    setUploadedFile(file)
    setActiveTab('reports')   // auto-route to Reports after classification
  }

  if (!user) return <LoginPage onLoginSuccess={handleLoginSuccess} />

  function renderPage() {
    switch (activeTab) {
      case 'home':     return <HomePage user={user} />
      case 'classify': return <ClassifyPage onResult={handleResult} />
      case 'reports':  return <ReportsPage result={result} onGoClassify={() => setActiveTab('classify')} />
      case 'rag':      return <RagPage uploadedFile={uploadedFile} result={result} />
      default:         return <HomePage user={user} />
    }
  }

  return (
    <div className="app-shell">
      <Header user={user} onLogout={handleLogout} onToggleSidebar={() => setSidebarCollapsed(v => !v)} />
      <div className="app-body">
        <Sidebar activeTab={activeTab} onTabChange={setActiveTab} hasResult={!!result} collapsed={sidebarCollapsed} onToggleCollapse={() => setSidebarCollapsed(v => !v)} />
        <main className="main-content">
          {renderPage()}
        </main>
      </div>
    </div>
  )
}
