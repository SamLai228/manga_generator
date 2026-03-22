import React, { useState, useEffect, useMemo, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import Lightbox from '../components/Lightbox'
import ImageEditPanel from '../components/ImageEditPanel'
import TagEditor from '../components/TagEditor'

const CATEGORY_LABELS = {
  species: '種族', hair: '髮型', clothing: '服裝',
  role: '角色', personality: '個性', custom: '自訂',
}

// ── Portrait Card (left grid) ────────────────────────────────────────────────

function CharacterPortraitCard({ character, isSelected, onClick }) {
  const [imgError, setImgError] = useState(false)
  const sheetUrl = `/api/characters/${character.id}/image/sheet.png`

  const personalityTags = (character.tags?.personality || []).slice(0, 2)

  return (
    <div
      className={`cs-portrait-card${isSelected ? ' cs-portrait-card--selected' : ''}`}
      onClick={onClick}
      role="button"
      aria-pressed={isSelected}
    >
      <div className="cs-portrait-frame">
        {imgError ? (
          <div className="cs-portrait-no-img">?</div>
        ) : (
          <img
            className="cs-portrait-img"
            src={sheetUrl}
            alt={character.name}
            onError={() => setImgError(true)}
            draggable={false}
          />
        )}
        <div className="cs-portrait-scanline" />
      </div>
      <div className="cs-portrait-footer">
        <div className="cs-portrait-name">{character.name}</div>
        {personalityTags.length > 0 && (
          <div className="cs-portrait-tags">
            {personalityTags.map(t => (
              <span key={t} className="cs-portrait-tag-pill">{t}</span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Empty right-panel placeholder ────────────────────────────────────────────

function EmptyDetailState() {
  return (
    <div className="cs-detail-empty">
      <div className="cs-detail-empty-icon">?</div>
      <div style={{ fontSize: 16, fontWeight: 600, color: '#8899aa' }}>選擇角色以查看詳細資料</div>
      <div className="cs-detail-empty-sub">使用方向鍵或點擊左側角色卡</div>
    </div>
  )
}

// ── Detail Panel (right side) ────────────────────────────────────────────────

function CharacterDetailPanel({ character, onDelete, onDuplicate, onTagsSaved, onNameSaved }) {
  const navigate = useNavigate()
  const [sheetVersion, setSheetVersion] = useState(() => Date.now())
  const [lightbox, setLightbox] = useState(false)
  const [editing, setEditing] = useState(false)
  const [editingTags, setEditingTags] = useState(false)
  const [editedTags, setEditedTags] = useState({})
  const [savingTags, setSavingTags] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [duplicating, setDuplicating] = useState(false)
  const [editingName, setEditingName] = useState(false)
  const [editedName, setEditedName] = useState('')
  const [savingName, setSavingName] = useState(false)

  // Reset all edit state when selected character changes
  useEffect(() => {
    setLightbox(false)
    setEditing(false)
    setEditingTags(false)
    setEditedTags(character?.tags || {})
    setSavingTags(false)
    setDeleting(false)
    setDuplicating(false)
    setSheetVersion(Date.now())
    setEditingName(false)
    setEditedName('')
    setSavingName(false)
  }, [character?.id])

  if (!character) return <EmptyDetailState />

  const sheetUrl = `/api/characters/${character.id}/image/sheet.png`

  const handleDelete = async () => {
    if (!window.confirm(`確定要刪除「${character.name}」嗎？`)) return
    setDeleting(true)
    try {
      await fetch(`/api/characters/${character.id}`, { method: 'DELETE' })
      onDelete(character.id)
    } catch {
      setDeleting(false)
    }
  }

  const handleDuplicate = async () => {
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

  const handleSaveName = async () => {
    const trimmed = editedName.trim()
    if (!trimmed || trimmed === character.name) { setEditingName(false); return }
    setSavingName(true)
    try {
      await fetch(`/api/characters/${character.id}/name`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: trimmed }),
      })
      setEditingName(false)
      onNameSaved(character.id, trimmed)
    } catch {}
    setSavingName(false)
  }

  const handleSaveTags = async () => {
    setSavingTags(true)
    try {
      await fetch(`/api/characters/${character.id}/tags`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tags: editedTags }),
      })
      setEditingTags(false)
      onTagsSaved(character.id, editedTags)
    } catch {}
    setSavingTags(false)
  }

  return (
    <div className="cs-detail-panel">
      {lightbox && (
        <Lightbox
          src={`${sheetUrl}?v=${sheetVersion}`}
          alt={`${character.name} sheet`}
          onClose={() => setLightbox(false)}
        />
      )}

      {/* Sheet image */}
      <div className="cs-detail-sheet-wrapper" onClick={() => setLightbox(true)}>
        <img
          className="cs-detail-sheet"
          src={`${sheetUrl}?v=${sheetVersion}`}
          alt={`${character.name} sheet`}
          onError={e => { e.target.style.display = 'none' }}
        />
        <div className="cs-detail-sheet-hint">點擊放大</div>
      </div>

      {/* Name + ID */}
      <div>
        {editingName ? (
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <input
              value={editedName}
              onChange={e => setEditedName(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') handleSaveName(); if (e.key === 'Escape') setEditingName(false) }}
              style={{ fontSize: 18, fontWeight: 700, padding: '4px 10px' }}
              autoFocus
            />
            <button className="btn btn-primary" onClick={handleSaveName} disabled={savingName} style={{ fontSize: 13, padding: '4px 12px' }}>
              {savingName ? '儲存...' : '確認'}
            </button>
            <button className="btn btn-secondary" onClick={() => setEditingName(false)} style={{ fontSize: 13, padding: '4px 12px' }}>取消</button>
          </div>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div className="cs-detail-name">{character.name}</div>
            <button
              className="btn btn-secondary"
              style={{ fontSize: 12, padding: '2px 8px' }}
              onClick={() => { setEditedName(character.name); setEditingName(true) }}
            >
              改名
            </button>
          </div>
        )}
        <div className="cs-detail-id">#{character.id}</div>
      </div>

      {/* Description */}
      {character.description && (
        <p className="cs-detail-desc">{character.description}</p>
      )}

      {/* Tags section */}
      {editingTags ? (
        <div>
          <TagEditor tags={editedTags} onChange={setEditedTags} />
          <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
            <button className="btn btn-primary" onClick={handleSaveTags} disabled={savingTags} style={{ fontSize: 13 }}>
              {savingTags ? '儲存中...' : '儲存標籤'}
            </button>
            <button className="btn btn-secondary" onClick={() => setEditingTags(false)} style={{ fontSize: 13 }}>
              取消
            </button>
          </div>
        </div>
      ) : (
        <div>
          <div className="cs-detail-tags-section">
            {Object.entries(character.tags || {}).map(([cat, tagList]) =>
              tagList && tagList.length > 0 ? (
                <div key={cat} className="tag-row-compact">
                  <span className="cat-label">{CATEGORY_LABELS[cat] || cat}：</span>
                  {tagList.map(t => <span key={t} className="tag">{t}</span>)}
                </div>
              ) : null
            )}
          </div>
          <button
            className="btn btn-secondary"
            style={{ fontSize: 13, marginTop: 8 }}
            onClick={() => { setEditedTags(character.tags || {}); setEditingTags(true) }}
          >
            編輯標籤
          </button>
        </div>
      )}

      {/* Image editing */}
      {editing ? (
        <ImageEditPanel
          characterId={character.id}
          filename="sheet.png"
          onUpdated={() => { setSheetVersion(Date.now()); setEditing(false) }}
          onCancel={() => setEditing(false)}
        />
      ) : (
        <button
          className="btn btn-secondary"
          style={{ fontSize: 13 }}
          onClick={() => setEditing(true)}
        >
          修改圖片
        </button>
      )}

      {/* Generate CTA */}
      <button
        className="btn btn-primary"
        style={{ width: '100%', justifyContent: 'center' }}
        onClick={() => navigate(`/generate?character=${character.id}`)}
      >
        用此角色生成漫畫 →
      </button>

      {/* Actions */}
      <div className="cs-detail-actions">
        <button
          className="btn btn-secondary"
          style={{ fontSize: 13 }}
          onClick={handleDuplicate}
          disabled={duplicating}
        >
          {duplicating ? '複製中...' : '製作副本'}
        </button>
        <button
          className="cs-btn-danger"
          onClick={handleDelete}
          disabled={deleting}
        >
          {deleting ? '刪除中...' : '刪除角色'}
        </button>
      </div>
    </div>
  )
}

// ── Page component ───────────────────────────────────────────────────────────

export default function CharacterLibrary() {
  const [characters, setCharacters] = useState([])
  const [selectedCharacterId, setSelectedCharacterId] = useState(null)
  const [search, setSearch] = useState('')
  const [tagFilter, setTagFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const gridRef = useRef(null)

  useEffect(() => {
    ;(async () => {
      try {
        const res = await fetch('/api/characters/')
        const data = await res.json()
        setCharacters(data)
      } catch (e) {
        console.error(e)
      }
      setLoading(false)
    })()
  }, [])

  const filteredCharacters = useMemo(() => {
    let list = characters
    if (search.trim()) {
      const q = search.trim().toLowerCase()
      list = list.filter(c => c.name.toLowerCase().includes(q))
    }
    if (tagFilter.trim()) {
      const q = tagFilter.trim().toLowerCase()
      list = list.filter(c => {
        const allTags = Object.values(c.tags || {}).flat()
        return allTags.some(t => t.toLowerCase().includes(q))
      })
    }
    return list
  }, [characters, search, tagFilter])

  const selectedCharacter = characters.find(c => c.id === selectedCharacterId) ?? null

  const handleNameSaved = (characterId, updatedName) => {
    setCharacters(prev => prev.map(c => c.id === characterId ? { ...c, name: updatedName } : c))
  }

  const handleTagsSaved = (characterId, updatedTags) => {
    setCharacters(prev => prev.map(c => c.id === characterId ? { ...c, tags: updatedTags } : c))
  }

  const handleDelete = (deletedId) => {
    setCharacters(prev => prev.filter(c => c.id !== deletedId))
    if (selectedCharacterId === deletedId) setSelectedCharacterId(null)
  }

  const handleDuplicate = (newCharacter) => {
    setCharacters(prev => [newCharacter, ...prev])
    setSelectedCharacterId(newCharacter.id)
  }

  // Keyboard navigation on the grid
  const handleGridKeyDown = (e) => {
    const cols = 3
    const keys = ['ArrowRight', 'ArrowLeft', 'ArrowDown', 'ArrowUp']
    if (!keys.includes(e.key)) return
    e.preventDefault()

    const currentIndex = filteredCharacters.findIndex(c => c.id === selectedCharacterId)

    if (currentIndex === -1) {
      if (filteredCharacters.length > 0) setSelectedCharacterId(filteredCharacters[0].id)
      return
    }

    let next = currentIndex
    if (e.key === 'ArrowRight') next = Math.min(currentIndex + 1, filteredCharacters.length - 1)
    if (e.key === 'ArrowLeft')  next = Math.max(currentIndex - 1, 0)
    if (e.key === 'ArrowDown')  next = Math.min(currentIndex + cols, filteredCharacters.length - 1)
    if (e.key === 'ArrowUp')    next = Math.max(currentIndex - cols, 0)

    if (next !== currentIndex) {
      setSelectedCharacterId(filteredCharacters[next].id)
      // Scroll the card into view
      const cards = gridRef.current?.querySelectorAll('.cs-portrait-card')
      if (cards?.[next]) {
        cards[next].scrollIntoView({ block: 'nearest', behavior: 'smooth' })
      }
    }
  }

  return (
    <div className="cs-page-layout">
      {/* ── Left panel ── */}
      <div className="cs-left-panel">
        <header className="cs-page-header">
          <div className="cs-header-row">
            <div>
              <p className="cs-header-eyebrow">Player Select</p>
              <h1 className="cs-header-title">角色圖庫</h1>
            </div>
            <span className="cs-header-count">{filteredCharacters.length} 個角色</span>
          </div>
        </header>

        <div className="cs-search-bar-group">
          <div className="cs-search-wrapper">
            <span className="cs-search-icon">🔍</span>
            <input
              className="cs-search-input"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="搜尋角色名稱..."
            />
          </div>
          <div className="cs-search-wrapper">
            <span className="cs-search-icon">🏷</span>
            <input
              className="cs-search-input"
              value={tagFilter}
              onChange={e => setTagFilter(e.target.value)}
              placeholder="篩選標籤..."
            />
          </div>
        </div>

        <div
          className="cs-portrait-grid"
          ref={gridRef}
          tabIndex={0}
          onKeyDown={handleGridKeyDown}
        >
          {loading ? (
            <div className="cs-loading">
              <div className="spinner" />
            </div>
          ) : filteredCharacters.length === 0 ? (
            <div className="cs-empty-library">
              {search || tagFilter
                ? <p>找不到符合的角色</p>
                : <p>尚無角色，前往角色工作室新增</p>
              }
            </div>
          ) : (
            filteredCharacters.map(c => (
              <CharacterPortraitCard
                key={c.id}
                character={c}
                isSelected={c.id === selectedCharacterId}
                onClick={() => {
                  setSelectedCharacterId(c.id)
                  gridRef.current?.focus()
                }}
              />
            ))
          )}
        </div>
      </div>

      {/* ── Right panel ── */}
      <div className="cs-right-panel">
        <CharacterDetailPanel
          character={selectedCharacter}
          onDelete={handleDelete}
          onDuplicate={handleDuplicate}
          onTagsSaved={handleTagsSaved}
          onNameSaved={handleNameSaved}
        />
      </div>
    </div>
  )
}
