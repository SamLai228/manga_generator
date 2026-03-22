import React, { useState } from 'react'

export default function MangaEditPanel({ jobId, onUpdated, onCancel }) {
  const [instruction, setInstruction] = useState('')
  const [refFiles, setRefFiles] = useState([])
  const [refPreviews, setRefPreviews] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleRefFiles = (e) => {
    const selected = Array.from(e.target.files)
    setRefFiles(selected)
    setRefPreviews(selected.map(f => URL.createObjectURL(f)))
  }

  const handleSubmit = async () => {
    if (!instruction.trim()) {
      setError('請輸入修改需求')
      return
    }
    setError('')
    setLoading(true)
    try {
      const fd = new FormData()
      fd.append('instruction', instruction)
      refFiles.forEach(f => fd.append('ref_files', f))
      const res = await fetch(`/api/manga/jobs/${jobId}/edit`, { method: 'POST', body: fd })
      if (!res.ok) {
        let msg = `HTTP ${res.status}`
        try { const j = await res.json(); msg += `: ${j.detail ?? JSON.stringify(j)}` } catch { msg += `: ${await res.text()}` }
        throw new Error(msg)
      }
      onUpdated()
    } catch (e) {
      setError(e.message)
      setLoading(false)
    }
  }

  return (
    <div className="img-edit-panel">
      {error && <div className="error-box" style={{ margin: 0 }}>{error}</div>}
      <textarea
        value={instruction}
        onChange={e => setInstruction(e.target.value)}
        placeholder="輸入修改需求，例：讓第一格的天空變成夜晚"
        disabled={loading}
      />
      <div>
        <label style={{ fontSize: 12, color: '#8899aa', display: 'block', marginBottom: 4 }}>
          附加參考圖片（選填）
        </label>
        <input
          type="file"
          accept="image/*"
          multiple
          onChange={handleRefFiles}
          disabled={loading}
          className="file-input"
        />
        {refPreviews.length > 0 && (
          <div className="preview-grid" style={{ marginTop: 6 }}>
            {refPreviews.map((url, i) => (
              <img key={i} src={url} alt={`ref ${i}`} className="preview-img" style={{ width: 48, height: 48 }} />
            ))}
          </div>
        )}
      </div>
      <div className="img-edit-panel-actions">
        <button className="btn btn-primary" onClick={handleSubmit} disabled={loading} style={{ flex: 1 }}>
          {loading ? <span className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} /> : '送出修改'}
        </button>
        <button className="btn btn-secondary" onClick={onCancel} disabled={loading}>
          取消
        </button>
      </div>
    </div>
  )
}
