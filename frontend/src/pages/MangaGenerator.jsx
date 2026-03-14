import React, { useState, useEffect, useRef } from 'react'


export default function MangaGenerator() {
  const [story, setStory] = useState('')
  const [styleHint, setStyleHint] = useState('manga, full color, clean lineart')
  const [jobId, setJobId] = useState(null)
  const [jobStatus, setJobStatus] = useState(null)
  const [script, setScript] = useState(null)
  const [error, setError] = useState('')
  const [previewScript, setPreviewScript] = useState(null)
  const [previewing, setPreviewing] = useState(false)
  const pollRef = useRef(null)

  // Poll job status
  useEffect(() => {
    if (!jobId) return
    const poll = async () => {
      try {
        const res = await fetch(`/api/manga/jobs/${jobId}`)
        const data = await res.json()
        setJobStatus(data)
        if (data.script) setScript(data.script)
        if (data.status === 'done' || data.status === 'error') {
          clearInterval(pollRef.current)
        }
      } catch (e) {}
    }
    poll()
    pollRef.current = setInterval(poll, 3000)
    return () => clearInterval(pollRef.current)
  }, [jobId])

  const previewParse = async () => {
    if (!story.trim()) { setError('請輸入劇情'); return }
    setError('')
    setPreviewing(true)
    try {
      const res = await fetch('/api/manga/parse', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ story_text: story, style_hint: styleHint }),
      })
      if (!res.ok) throw new Error(await res.text())
      setPreviewScript(await res.json())
    } catch (e) {
      setError(e.message)
    }
    setPreviewing(false)
  }

  const generate = async () => {
    if (!story.trim()) { setError('請輸入劇情'); return }
    setError('')
    setJobId(null); setJobStatus(null); setScript(null)
    try {
      const res = await fetch('/api/manga/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ story_text: story, style_hint: styleHint }),
      })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      setJobId(data.job_id)
    } catch (e) {
      setError(e.message)
    }
  }

  const isGenerating = jobStatus && (jobStatus.status === 'pending' || jobStatus.status === 'processing')
  const isDone = jobStatus && jobStatus.status === 'done'
  const isError = jobStatus && jobStatus.status === 'error'

  return (
    <div>
      <h1 className="section-title">四格漫畫生成器</h1>

      {error && <div className="error-box">{error}</div>}

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="form-group">
          <label>劇情描述</label>
          <textarea
            value={story}
            onChange={e => setStory(e.target.value)}
            placeholder="例：小明看到一隻貓，開心地追著貓跑，結果摔倒了，貓回頭看著他。"
            rows={4}
          />
        </div>
        <div className="form-group">
          <label>畫風提示</label>
          <input
            value={styleHint}
            onChange={e => setStyleHint(e.target.value)}
            placeholder="manga, black and white, clean lineart"
          />
        </div>
        <div style={{ display: 'flex', gap: 12 }}>
          <button className="btn btn-secondary" onClick={previewParse} disabled={previewing}>
            {previewing ? '解析中...' : '預覽腳本'}
          </button>
          <button className="btn btn-primary" onClick={generate} disabled={isGenerating}>
            {isGenerating ? '生成中...' : '生成四格漫畫'}
          </button>
        </div>
      </div>

      {previewScript && !jobId && (
        <div className="card" style={{ marginBottom: 20 }}>
          <h3 style={{ margin: '0 0 16px', fontSize: 16 }}>腳本預覽：{previewScript.title}</h3>
          <div className="script-grid">
            {previewScript.panels.map(p => (
              <div key={p.panel_number} className="script-panel">
                <div className="panel-num">格 {p.panel_number}</div>
                <div><strong>場景：</strong>{p.scene}</div>
                <div><strong>動作：</strong>{p.action}</div>
                <div><strong>角色：</strong>{p.characters.join(', ') || '無'}</div>
                {p.dialogue && <div><strong>對白：</strong>「{p.dialogue}」</div>}
                <div><strong>鏡頭：</strong>{p.camera}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {jobId && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ margin: 0, fontSize: 16 }}>
              生成任務 #{jobId}
              {' '}
              <span className={`status-badge status-${jobStatus?.status}`}>
                {jobStatus?.status || 'pending'}
              </span>
            </h3>
          </div>

          {script && (
            <p style={{ color: '#8899aa', marginBottom: 16 }}>{script.title}</p>
          )}

          {isGenerating && (
            <div className="center">
              <div className="spinner" />
              <p>正在生成漫畫，請稍候...</p>
            </div>
          )}

          {isDone && (
            <div style={{ textAlign: 'center' }}>
              <img
                src={`/api/manga/jobs/${jobId}/page`}
                alt="四格漫畫"
                style={{ maxWidth: '100%', borderRadius: 8, marginBottom: 16 }}
              />
              <div>
                <a
                  href={`/api/manga/jobs/${jobId}/page`}
                  download={`manga_${jobId}.png`}
                  className="btn btn-primary"
                >
                  下載漫畫
                </a>
              </div>
            </div>
          )}

          {isError && (
            <div className="error-box">生成失敗：{jobStatus.error}</div>
          )}
        </div>
      )}
    </div>
  )
}
