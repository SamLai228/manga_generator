import React, { useState, useEffect } from 'react'
import Lightbox from '../components/Lightbox'
import ImageEditPanel from '../components/ImageEditPanel'

const CATEGORY_LABELS = {
  species: '種族', hair: '髮型', clothing: '服裝',
  role: '角色', personality: '個性', custom: '自訂',
}

function CharacterCard({ character, onDelete, onDuplicate }) {
  const [expanded, setExpanded] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [duplicating, setDuplicating] = useState(false)
  const [lightbox, setLightbox] = useState(false)
  const [editing, setEditing] = useState(false)
  const [sheetVersion, setSheetVersion] = useState(() => Date.now())
  const sheetUrl = `/api/characters/${character.id}/image/sheet.png`

  const handleDelete = async (e) => {
    e.stopPropagation()
    if (!window.confirm(`確定要刪除「${character.name}」嗎？`)) return
    setDeleting(true)
    try {
      await fetch(`/api/characters/${character.id}`, { method: 'DELETE' })
      onDelete(character.id)
    } catch {
      setDeleting(false)
    }
  }

  const handleDuplicate = async (e) => {
    e.stopPropagation()
    setDuplicating(true)
    try {
      const res = await fetch(`/api/characters/${character.id}/duplicate`, { method: 'POST' })
      const newCharacter = await res.json()
      onDuplicate(newCharacter)
    } catch {
      // silent fail
    }
    setDuplicating(false)
  }

  return (
    <div className="char-card card">
      {lightbox && <Lightbox src={`${sheetUrl}?v=${sheetVersion}`} alt={`${character.name} sheet`} onClose={() => setLightbox(false)} />}
      <div className="char-card-header" onClick={() => setExpanded(!expanded)}>
        <div>
          <div className="char-name">{character.name}</div>
          <div className="char-id">#{character.id}</div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button
            className="btn btn-secondary"
            onClick={handleDuplicate}
            disabled={duplicating}
            style={{ fontSize: 12, padding: '2px 10px' }}
          >
            {duplicating ? '...' : '製作副本'}
          </button>
          <button
            className="btn btn-secondary"
            onClick={handleDelete}
            disabled={deleting}
            style={{ fontSize: 12, padding: '2px 10px', color: '#e05555' }}
          >
            {deleting ? '...' : '刪除'}
          </button>
          <span>{expanded ? '▲' : '▼'}</span>
        </div>
      </div>

      {expanded && (
        <div className="char-card-body">
          <img
            src={`${sheetUrl}?v=${sheetVersion}`}
            alt={`${character.name} sheet`}
            className="char-sheet-img"
            onError={e => { e.target.style.display = 'none' }}
            onClick={e => { e.stopPropagation(); setLightbox(true) }}
          />
          {!editing ? (
            <button
              className="btn btn-secondary"
              style={{ fontSize: 12, padding: '2px 10px', marginTop: 6 }}
              onClick={() => setEditing(true)}
            >
              修改圖片
            </button>
          ) : (
            <ImageEditPanel
              characterId={character.id}
              filename="sheet.png"
              onUpdated={() => { setSheetVersion(Date.now()); setEditing(false) }}
              onCancel={() => setEditing(false)}
            />
          )}
          {character.description && (
            <p className="info-text">{character.description}</p>
          )}
          <div className="tags-section">
            {Object.entries(character.tags || {}).map(([cat, tagList]) =>
              tagList && tagList.length > 0 ? (
                <div key={cat} className="tag-row-compact">
                  <span className="cat-label">{CATEGORY_LABELS[cat] || cat}：</span>
                  {tagList.map(t => <span key={t} className="tag">{t}</span>)}
                </div>
              ) : null
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default function CharacterLibrary() {
  const [characters, setCharacters] = useState([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState(null)

  useEffect(() => {
    fetchCharacters()
    fetchStats()
  }, [])

  const fetchCharacters = async (name = '') => {
    setLoading(true)
    try {
      const url = name ? `/api/characters/?name=${encodeURIComponent(name)}` : '/api/characters/'
      const res = await fetch(url)
      const data = await res.json()
      setCharacters(data)
    } catch (e) {
      console.error(e)
    }
    setLoading(false)
  }

  const fetchStats = async () => {
    try {
      const res = await fetch('/api/characters/stats')
      setStats(await res.json())
    } catch (e) {}
  }

  const handleSearch = (e) => {
    const val = e.target.value
    setSearch(val)
    fetchCharacters(val)
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h1 className="section-title" style={{ margin: 0 }}>角色圖庫</h1>
        {stats && (
          <span style={{ color: '#8899aa', fontSize: 14 }}>共 {stats.total_characters} 個角色</span>
        )}
      </div>

      <input
        value={search}
        onChange={handleSearch}
        placeholder="搜尋角色名稱..."
        style={{ marginBottom: 20 }}
      />

      {loading ? (
        <div className="card center"><div className="spinner" /></div>
      ) : characters.length === 0 ? (
        <div className="card center">
          <p style={{ color: '#8899aa' }}>
            {search ? `找不到「${search}」` : '尚無角色，前往角色工作室新增'}
          </p>
        </div>
      ) : (
        <div className="char-grid">
          {characters.map(c => (
            <CharacterCard
              key={c.id}
              character={c}
              onDelete={id => setCharacters(prev => prev.filter(x => x.id !== id))}
              onDuplicate={newChar => setCharacters(prev => [newChar, ...prev])}
            />
          ))}
        </div>
      )}
    </div>
  )
}
