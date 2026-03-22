import React, { useState, useEffect, useRef } from 'react'

export default function CharacterPicker({ selectedIds, onChange }) {
  const [allCharacters, setAllCharacters] = useState([])
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const browserRef = useRef(null)

  useEffect(() => {
    fetch('/api/characters/')
      .then(r => r.json())
      .then(data => setAllCharacters(data))
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (!open) return
    const handleClick = (e) => {
      if (browserRef.current && !browserRef.current.contains(e.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open])

  const selectedChars = selectedIds
    .map(id => allCharacters.find(c => c.id === id))
    .filter(Boolean)

  const filtered = allCharacters.filter(c =>
    c.name.toLowerCase().includes(search.toLowerCase()) ||
    c.id.toLowerCase().includes(search.toLowerCase())
  )

  const toggle = (id) => {
    if (selectedIds.includes(id)) {
      onChange(selectedIds.filter(x => x !== id))
    } else if (selectedIds.length < 5) {
      onChange([...selectedIds, id])
    }
  }

  const remove = (id) => {
    onChange(selectedIds.filter(x => x !== id))
  }

  return (
    <div ref={browserRef}>
      <div className="char-picker-selected">
        {selectedChars.map(c => (
          <div key={c.id} className="char-picker-chip">
            <div className="char-picker-chip-portrait">
              <img className="char-picker-chip-portrait-img" src={`/api/characters/${c.id}/image/sheet.png`} alt={c.name} />
              <div className="cs-portrait-scanline" />
            </div>
            <span className="char-picker-chip-name">{c.name}</span>
            <button className="char-picker-remove" onClick={() => remove(c.id)}>×</button>
          </div>
        ))}
        {selectedIds.length < 5 && (
          <button
            className="char-picker-add-btn"
            onClick={() => setOpen(o => !o)}
            type="button"
          >
            +
          </button>
        )}
      </div>

      {open && (
        <div className="char-picker-browser">
          <input
            className="char-picker-search"
            placeholder="搜尋角色名稱或 ID..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            autoFocus
          />
          <div className="char-picker-list">
            {filtered.length === 0 && (
              <div style={{ color: '#8899aa', fontSize: 13, padding: '8px 0' }}>沒有符合的角色</div>
            )}
            {filtered.map(c => {
              const isSelected = selectedIds.includes(c.id)
              const isDisabled = !isSelected && selectedIds.length >= 5
              return (
                <div
                  key={c.id}
                  className={`char-picker-row${isSelected ? ' selected' : ''}${isDisabled ? ' disabled' : ''}`}
                  onClick={() => !isDisabled && toggle(c.id)}
                >
                  <div className="char-picker-row-portrait">
                    <img className="char-picker-row-portrait-img" src={`/api/characters/${c.id}/image/sheet.png`} alt={c.name} />
                  </div>
                  <div className="char-picker-row-info">
                    <strong>{c.name}</strong>
                    <span>{c.id}</span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
