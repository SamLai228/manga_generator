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

function TagEditor({ tags, onChange }) {
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
              placeholder={`新增標籤...`}
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

export default function CharacterStudio() {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [photoFiles, setPhotoFiles] = useState([])
  const [photoUrls, setPhotoUrls] = useState([])
  const [styleFiles, setStyleFiles] = useState([])
  const [styleUrls, setStyleUrls] = useState([])
  const [step, setStep] = useState('input') // input | analyzing | confirm | registering | done
  const [suggestedTags, setSuggestedTags] = useState({})
  const [confirmedTags, setConfirmedTags] = useState({})
  const [suggestedStyle, setSuggestedStyle] = useState('')
  const [suggestedDesc, setSuggestedDesc] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  const handlePhotoFiles = (e) => {
    const selected = Array.from(e.target.files)
    setPhotoFiles(selected)
    setPhotoUrls(selected.map(f => URL.createObjectURL(f)))
  }

  const handleStyleFiles = (e) => {
    const selected = Array.from(e.target.files)
    setStyleFiles(selected)
    setStyleUrls(selected.map(f => URL.createObjectURL(f)))
  }

  const analyze = async () => {
    if (!name.trim()) { setError('請輸入角色名稱'); return }
    setError('')
    setStep('analyzing')
    try {
      const fd = new FormData()
      photoFiles.forEach(f => fd.append('photo_files', f))
      styleFiles.forEach(f => fd.append('style_files', f))
      fd.append('name', name)
      fd.append('additional_description', description)
      const res = await fetch('/api/characters/analyze', { method: 'POST', body: fd })
      if (!res.ok) {
        let msg = `HTTP ${res.status}`
        try { const j = await res.json(); msg += `: ${j.detail ?? JSON.stringify(j)}` } catch { msg += `: ${await res.text()}` }
        throw new Error(msg)
      }
      const data = await res.json()
      setSuggestedTags(data.suggested_tags || {})
      setConfirmedTags(data.suggested_tags || {})
      setSuggestedStyle(data.style_description || '')
      setSuggestedDesc(data.description || '')
      setStep('confirm')
    } catch (e) {
      setError(e.message)
      setStep('input')
    }
  }

  const register = async () => {
    setStep('registering')
    setError('')
    try {
      const fd = new FormData()
      photoFiles.forEach(f => fd.append('photo_files', f))
      styleFiles.forEach(f => fd.append('style_files', f))
      fd.append('name', name)
      fd.append('additional_description', description)
      fd.append('generate_angles', 'true')
      fd.append('tags_json', JSON.stringify(confirmedTags))
      const res = await fetch('/api/characters/register', { method: 'POST', body: fd })
      if (!res.ok) {
        let msg = `HTTP ${res.status}`
        try { const j = await res.json(); msg += `: ${j.detail ?? JSON.stringify(j)}` } catch { msg += `: ${await res.text()}` }
        throw new Error(msg)
      }
      const data = await res.json()
      setResult(data)
      setStep('done')
    } catch (e) {
      setError(e.message)
      setStep('confirm')
    }
  }

  const reset = () => {
    setName(''); setDescription('')
    setPhotoFiles([]); setPhotoUrls([]); setStyleFiles([]); setStyleUrls([])
    setStep('input'); setSuggestedTags({}); setConfirmedTags({})
    setSuggestedStyle(''); setSuggestedDesc(''); setResult(null); setError('')
  }

  return (
    <div>
      <h1 className="section-title">角色工作室</h1>

      {error && <div className="error-box">{error}</div>}

      {step === 'input' && (
        <div className="card">
          <div className="form-group">
            <label>角色名稱 *</label>
            <input value={name} onChange={e => setName(e.target.value)} placeholder="例：小明" />
          </div>
          <div className="form-group">
            <label>角色描述（選填）</label>
            <textarea
              value={description}
              onChange={e => setDescription(e.target.value)}
              placeholder="簡短描述角色外貌、個性、背景故事..."
              rows={3}
            />
          </div>
          <div className="form-group">
            <label>真實照片（1-5張，選填）</label>
            <p className="hint" style={{ margin: '4px 0 8px' }}>用於分析角色特徵與外貌</p>
            <input type="file" accept="image/*" multiple onChange={handlePhotoFiles} className="file-input" />
            {photoUrls.length > 0 && (
              <div className="preview-grid">
                {photoUrls.map((url, i) => (
                  <img key={i} src={url} alt={`photo ${i}`} className="preview-img" />
                ))}
              </div>
            )}
          </div>
          <div className="form-group">
            <label>漫畫風格參考（1-3張，選填）</label>
            <p className="hint" style={{ margin: '4px 0 8px' }}>用於提取畫風，生成漫畫角色圖</p>
            <input type="file" accept="image/*" multiple onChange={handleStyleFiles} className="file-input" />
            {styleUrls.length > 0 && (
              <div className="preview-grid">
                {styleUrls.map((url, i) => (
                  <img key={i} src={url} alt={`style ${i}`} className="preview-img" />
                ))}
              </div>
            )}
          </div>
          <button className="btn btn-primary" onClick={analyze}>
            分析角色 →
          </button>
        </div>
      )}

      {step === 'analyzing' && (
        <div className="card center">
          <div className="spinner" />
          <p>正在使用 Gemini AI 分析角色特徵...</p>
        </div>
      )}

      {step === 'confirm' && (
        <div className="card">
          <h2 style={{ margin: '0 0 16px', fontSize: 16 }}>確認角色資訊</h2>
          <div className="form-group">
            <label>AI 生成描述</label>
            <p className="info-text">{suggestedDesc}</p>
          </div>
          <div className="form-group">
            <label>畫風描述</label>
            <p className="info-text">{suggestedStyle}</p>
          </div>
          <div className="form-group">
            <label>標籤（可修改）</label>
            <TagEditor tags={confirmedTags} onChange={setConfirmedTags} />
          </div>
          <div style={{ display: 'flex', gap: 12, marginTop: 20 }}>
            <button className="btn btn-secondary" onClick={() => setStep('input')}>← 返回</button>
            <button className="btn btn-primary" onClick={register}>
              確認並入庫 →
            </button>
          </div>
        </div>
      )}

      {step === 'registering' && (
        <div className="card center">
          <div className="spinner" />
          <p>正在生成多角度角色圖表並入庫...</p>
          <p className="hint">這需要約 1-2 分鐘</p>
        </div>
      )}

      {step === 'done' && result && (
        <div className="card">
          <div className="success-header">
            角色「{result.name}」已成功入庫！
          </div>
          <p className="info-text">ID: {result.id}</p>
          {result.angles && result.angles.length > 0 && (
            <div>
              <label>生成的角度圖</label>
              <div className="preview-grid">
                {result.angles.map(angle => (
                  <img
                    key={angle}
                    src={`/api/characters/${result.id}/image/${angle}`}
                    alt={angle}
                    className="preview-img"
                  />
                ))}
              </div>
            </div>
          )}
          <button className="btn btn-primary" onClick={reset} style={{ marginTop: 16 }}>
            新增另一個角色
          </button>
        </div>
      )}
    </div>
  )
}
