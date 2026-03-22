import React, { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import MangaEditPanel from '../components/MangaEditPanel'
import Lightbox from '../components/Lightbox'

const STATUS_LABEL = { pending: '等待中', processing: '生成中', done: '完成', error: '失敗' }
const STATUS_CLASS = { pending: 'status-pending', processing: 'status-processing', done: 'status-done', error: 'status-error' }

function formatDate(dateStr) {
  if (!dateStr) return ''
  try { return new Date(dateStr).toLocaleString('zh-TW') } catch { return dateStr }
}

export default function MangaHistory() {
  const navigate = useNavigate()
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)
  const [editingJobId, setEditingJobId] = useState(null)
  const [imgKeys, setImgKeys] = useState({})
  const [lightboxJobId, setLightboxJobId] = useState(null)
  const [duplicating, setDuplicating] = useState(null)

  const handleDuplicate = async (jobId) => {
    setDuplicating(jobId)
    try {
      const res = await fetch(`/api/manga/jobs/${jobId}/duplicate`, { method: 'POST' })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const newJob = await res.json()
      setJobs(prev => [newJob, ...prev])
    } catch (e) {
      alert(`製作副本失敗：${e.message}`)
    }
    setDuplicating(null)
  }

  useEffect(() => {
    fetch('/api/manga/jobs')
      .then(r => r.json())
      .then(data => { setJobs(data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  const lightboxJob = lightboxJobId ? jobs.find(j => j.id === lightboxJobId) : null

  return (
    <div>
      {lightboxJob && (
        <Lightbox
          src={`/api/manga/jobs/${lightboxJob.id}/page${imgKeys[lightboxJob.id] ? `?t=${imgKeys[lightboxJob.id]}` : ''}`}
          alt={`manga ${lightboxJob.id}`}
          onClose={() => setLightboxJobId(null)}
        />
      )}
      <h1 className="section-title">生成歷史</h1>

      {loading ? (
        <div className="card center"><div className="spinner" /></div>
      ) : jobs.length === 0 ? (
        <div className="card center">
          <p style={{ color: '#8899aa' }}>
            尚無生成記錄，前往 <Link to="/generate">生成漫畫</Link> 開始
          </p>
        </div>
      ) : (
        <div>
          {jobs.map(job => (
            <div key={job.id} className="card" style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                <div>
                  <span style={{ fontWeight: 600, marginRight: 8 }}>#{job.id}</span>
                  <span className={`status-badge ${STATUS_CLASS[job.status] || ''}`}>
                    {STATUS_LABEL[job.status] || job.status}
                  </span>
                </div>
                <span style={{ color: '#8899aa', fontSize: 13 }}>{formatDate(job.created_at)}</span>
              </div>

              {job.story_text && (
                <p style={{ color: '#ccd', margin: '4px 0 8px', fontSize: 14, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {job.story_text}
                </p>
              )}

              {job.script?.title && (
                <p style={{ color: '#8899aa', fontSize: 13, margin: '0 0 8px' }}>腳本：{job.script.title}</p>
              )}

              {job.status === 'done' && (
                <div>
                  <div
                    className="cs-detail-sheet-wrapper"
                    style={{ marginBottom: 8 }}
                    onClick={() => setLightboxJobId(job.id)}
                  >
                    <img
                      key={imgKeys[job.id] || 0}
                      src={`/api/manga/jobs/${job.id}/page${imgKeys[job.id] ? `?t=${imgKeys[job.id]}` : ''}`}
                      alt={`manga ${job.id}`}
                      style={{ maxWidth: '100%', maxHeight: 300, borderRadius: 6, display: 'block' }}
                      onError={e => { e.target.parentElement.style.display = 'none' }}
                    />
                    <div className="cs-detail-sheet-hint">點擊放大</div>
                  </div>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: editingJobId === job.id ? 12 : 0 }}>
                    <a
                      href={`/api/manga/jobs/${job.id}/page`}
                      download={`manga_${job.id}.png`}
                      className="btn btn-secondary"
                      style={{ fontSize: 13 }}
                    >
                      下載漫畫
                    </a>
                    <button
                      className="btn btn-secondary"
                      style={{ fontSize: 13 }}
                      onClick={() => setEditingJobId(id => id === job.id ? null : job.id)}
                    >
                      {editingJobId === job.id ? '收合修改' : '修改漫畫'}
                    </button>
                    <button
                      className="btn btn-secondary"
                      style={{ fontSize: 13 }}
                      onClick={() => handleDuplicate(job.id)}
                      disabled={duplicating === job.id}
                    >
                      {duplicating === job.id ? '複製中...' : '製作副本'}
                    </button>
                    {job.story_text && (
                      <button
                        className="btn btn-secondary"
                        style={{ fontSize: 13 }}
                        onClick={() => navigate(`/generate?story=${encodeURIComponent(job.story_text)}`)}
                      >
                        用同一故事重新生成
                      </button>
                    )}
                  </div>
                  {editingJobId === job.id && (
                    <MangaEditPanel
                      jobId={job.id}
                      onUpdated={() => {
                        setEditingJobId(null)
                        setImgKeys(k => ({ ...k, [job.id]: Date.now() }))
                      }}
                      onCancel={() => setEditingJobId(null)}
                    />
                  )}
                </div>
              )}

              {job.status === 'error' && (
                <div>
                  {job.error && <div className="error-box" style={{ marginTop: 8 }}>失敗原因：{job.error}</div>}
                  {job.story_text && (
                    <button
                      className="btn btn-secondary"
                      style={{ fontSize: 13, marginTop: 8 }}
                      onClick={() => navigate(`/generate?story=${encodeURIComponent(job.story_text)}`)}
                    >
                      重試
                    </button>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
