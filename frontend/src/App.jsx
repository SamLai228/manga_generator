import React from 'react'
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import CharacterStudio from './pages/CharacterStudio.jsx'
import CharacterLibrary from './pages/CharacterLibrary.jsx'
import MangaGenerator from './pages/MangaGenerator.jsx'
import './App.css'

class ErrorBoundary extends React.Component {
  constructor(props) { super(props); this.state = { error: null } }
  static getDerivedStateFromError(e) { return { error: e } }
  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: 32 }}>
          <div className="error-box">
            <strong>頁面發生錯誤：</strong> {this.state.error.message}
          </div>
          <button className="btn btn-secondary" style={{ marginTop: 16 }}
            onClick={() => this.setState({ error: null })}>重試</button>
        </div>
      )
    }
    return this.props.children
  }
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <nav className="navbar">
          <div className="navbar-brand">四格漫畫生成器</div>
          <div className="navbar-links">
            <NavLink to="/" end className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
              角色工作室
            </NavLink>
            <NavLink to="/library" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
              角色圖庫
            </NavLink>
            <NavLink to="/generate" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
              生成漫畫
            </NavLink>
          </div>
        </nav>
        <main className="main-content">
          <ErrorBoundary>
            <Routes>
              <Route path="/" element={<CharacterStudio />} />
              <Route path="/library" element={<CharacterLibrary />} />
              <Route path="/generate" element={<MangaGenerator />} />
            </Routes>
          </ErrorBoundary>
        </main>
      </div>
    </BrowserRouter>
  )
}
