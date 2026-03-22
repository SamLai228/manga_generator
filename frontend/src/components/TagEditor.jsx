import React, { useState } from 'react'

const TAG_CATEGORIES = ['species', 'hair', 'clothing', 'role', 'personality', 'custom']
const CATEGORY_LABELS = {
  species: '種族',
  hair: '髮型/髮色',
  clothing: '服裝',
  role: '角色定位',
  personality: '個性',
  custom: '自訂特徵',
}

export default function TagEditor({ tags, onChange }) {
  const [inputs, setInputs] = useState({})

  const addTag = (category) => {
    const val = (inputs[category] || '').trim()
    if (!val) return
    const current = tags[category] || []
    if (!current.includes(val)) {
      onChange({ ...tags, [category]: [...current, val] })
    }
    setInputs({ ...inputs, [category]: '' })
  }

  const removeTag = (category, tag) => {
    onChange({ ...tags, [category]: (tags[category] || []).filter(t => t !== tag) })
  }

  return (
    <div className="tag-editor">
      {TAG_CATEGORIES.map(cat => (
        <div key={cat} className="tag-row">
          <label>{CATEGORY_LABELS[cat]}</label>
          <div className="tag-input-row">
            <input
              value={inputs[cat] || ''}
              onChange={e => setInputs({ ...inputs, [cat]: e.target.value })}
              onKeyDown={e => e.key === 'Enter' && addTag(cat)}
              placeholder="新增標籤..."
              style={{ flex: 1, marginRight: 8 }}
            />
            <button className="btn btn-secondary" onClick={() => addTag(cat)} style={{ width: 60 }}>
              +
            </button>
          </div>
          <div className="tags-display">
            {(tags[cat] || []).map(tag => (
              <span key={tag} className="tag">
                {tag}
                <button className="tag-remove" onClick={() => removeTag(cat, tag)}>×</button>
              </span>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
