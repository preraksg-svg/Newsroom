import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { useStore, API_BASE } from '../store'

function Loader({ message }) {
  return (
    <div className="flex-center" style={{ flex: 1, height: '100%', flexDirection: 'column', color: 'var(--text-muted)' }}>
      <div className="loader-spinner"></div>
      <div style={{ marginTop: '20px', fontSize: '0.7rem', letterSpacing: '2px', fontWeight: 800 }}>{message}</div>
    </div>
  )
}

function EmptyState({ title, subtitle }) {
  return (
    <div className="flex-center" style={{ flex: 1, height: '100%', textAlign: 'center', padding: '40px' }}>
      <div>
        <div style={{ fontSize: '3rem', marginBottom: '20px' }}>📂</div>
        <div style={{ fontWeight: 800, color: '#fff', marginBottom: '10px', fontSize: '1.2rem' }}>{title}</div>
        <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem', letterSpacing: '1px' }}>{subtitle}</div>
      </div>
    </div>
  )
}

function ArticleCard({ item, onClick }) {
  const fields = item.fields || item
  const status = fields.status || 'Draft'
  const score = fields.final_score || 0
  
  let summary = ''
  try {
    const ai = fields.ai_summary ? (typeof fields.ai_summary === 'string' ? JSON.parse(fields.ai_summary) : fields.ai_summary) : null
    summary = ai?.summary || ''
  } catch(e) {}

  return (
    <div className="news-card" onClick={onClick}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
        <span className={`badge badge-outline ${status === 'Published' ? 'badge-cyan' : (status === 'Approved' ? 'badge-green' : 'badge-orange')}`}>
          {status}
        </span>
        <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>
          {item.createdTime ? new Date(item.createdTime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}
        </span>
      </div>
      <h3 className="card-title">{fields.title}</h3>
      <p className="card-summary">{summary || 'Intelligence extraction in progress...'}</p>
      <div className="score-meter">
        <div className="score-fill" style={{ width: `${score}%`, background: score > 70 ? 'var(--c-green)' : 'var(--c-cyan)' }} />
      </div>
    </div>
  )
}

export default function NewsFeed({ isRecycleBin }) {
  const navigate = useNavigate()
  const { searchQuery, statusFilter } = useStore()
  
  const { data, isLoading, isError } = useQuery({
    queryKey: ['news-kanban', isRecycleBin, searchQuery, statusFilter],
    queryFn: async () => {
      const endpoint = isRecycleBin ? `${API_BASE}/api/rejected` : `${API_BASE}/api/news`
      const params = new URLSearchParams()
      if (searchQuery) params.append('search', searchQuery)
      if (!isRecycleBin && statusFilter) params.append('status', statusFilter)
      
      const res = await fetch(`${endpoint}?${params.toString()}`)
      if (!res.ok) throw new Error('API_ERROR')
      const json = await res.json()
      // Return the items array nested inside the api response object
      return json.data?.items || json.data || []
    }
  })

  const columns = useMemo(() => {
    if (!data) return {}
    if (isRecycleBin) return { 'Recycle Bin': data }
    
    return {
      'Draft':     data.filter(i => (i.fields?.status || i.status) === 'Draft'),
      'Approved':  data.filter(i => (i.fields?.status || i.status) === 'Approved'),
      'Published': data.filter(i => (i.fields?.status || i.status) === 'Published'),
      'Failed':    data.filter(i => (i.fields?.status || i.status) === 'Failed')
    }
  }, [data, isRecycleBin])

  if (isLoading) return <Loader message="SYNCHRONIZING KANBAN DATA..." />
  if (isError) return <EmptyState title="API CONNECTION FAILED" subtitle="PLEASE ENSURE BACKEND IS RUNNING ON PORT 8000" />
  if (!data || data.length === 0) return <EmptyState title="NO SIGNALS DETECTED" subtitle="TRIGGER THE SYSTEM PIPELINE TO INGEST NEW CONTENT" />

  return (
    <div className="kanban-board">
      {Object.entries(columns).map(([name, items]) => (
        <div key={name} className="kanban-column">
          <div className="column-header">
            <span>{name}</span>
            <span style={{ opacity: 0.5 }}>{items.length}</span>
          </div>
          <div className="column-content">
            {items.map(item => (
              <ArticleCard key={item.id} item={item} onClick={() => navigate(`/article/${item.id}`)} />
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
