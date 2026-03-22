import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'

const STATUS_LABEL = { pending: '等待中', processing: '生成中', done: '完成', error: '失敗' }
const STATUS_CLASS = { pending: 'status-pending', processing: 'status-processing', done: 'status-done', error: 'status-error' }

function formatDate(dateStr) {
  if (!dateStr) return ''
  try { return new Date(dateStr).toLocaleString('zh-TW') } catch { return dateStr }
}

export default function MangaHistory() {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/manga/jobs')
      .then(r => r.json())
      .then(data => { setJobs(data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  return (
    <div>
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
                  <img
                    src={`/api/manga/jobs/${job.id}/page`}
                    alt={`manga ${job.id}`}
                    style={{ maxWidth: '100%', maxHeight: 300, borderRadius: 6, marginBottom: 8, display: 'block' }}
                    onError={e => { e.target.style.display = 'none' }}
                  />
                  <a
                    href={`/api/manga/jobs/${job.id}/page`}
                    download={`manga_${job.id}.png`}
                    className="btn btn-secondary"
                    style={{ fontSize: 13 }}
                  >
                    下載漫畫
                  </a>
                </div>
              )}

              {job.status === 'error' && job.error && (
                <div className="error-box" style={{ marginTop: 8 }}>失敗原因：{job.error}</div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
