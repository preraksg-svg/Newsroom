import { useMemo, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Trash2, ExternalLink, Calendar, Star, AlertCircle, RefreshCw, RotateCcw } from 'lucide-react'
import { useStore } from '../store'
import { NewsService } from '../services/api'
import { Loader, EmptyState, ErrorState } from '../components/StatusStates'

function ArticleCard({ item, onClick, onReject, onRestore, onAction, isRecycleBin }) {
  const navigate = useNavigate()
  const fields = item.fields || item
  const status = fields.status || fields.Status || item.status || 'Draft'
  const score = fields.final_score || fields.finalScore || fields['Final Score'] || 0
  const isVerified = true // (score >= 0) -> All news verified
  
  const title = fields.title || fields.Title || fields.headline || 'UNTITLED SIGNAL'
  const publisher = fields.publisher || fields.Publisher || 'Global Node'
  const summary = fields.summary_preview || fields.summary || fields['Summary Preview'] || ''
  const createdTime = fields.createdTime || fields.created_at || item.createdTime || new Date()

  const handleReject = (e) => {
    e.stopPropagation()
    if (confirm('REJECT SIGNAL? Intelligence will be moved to Recycle Bin.')) {
      onReject(item.id)
    }
  }

  const handleRestore = (e) => {
    e.stopPropagation()
    onRestore(item.id)
  }

  const handleApprove = (e) => {
    e.stopPropagation()
    onAction('approve_article', item.id)
  }

  const handleRevertToDraft = (e) => {
    e.stopPropagation()
    if (confirm('Move this article back to Drafts?')) {
      onAction('revert_to_draft', item.id)
    }
  }

  const handlePublish = (e) => {
    e.stopPropagation()
    // Navigate to the article detail view first, passing state so ArticleView knows to trigger the publishing and open the split view
    navigate(`/article/${item.id}`, { state: { triggerPublish: true } })
  }

  return (
    <div className="news-card animate-fade-in" onClick={onClick}>
      <span className={`badge ${isVerified ? 'badge-green' : 'badge-cyan'}`}>
        {isVerified ? 'VERIFIED' : 'SIGNAL'}
      </span>

      <div style={{ marginBottom: '16px', fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-data)', letterSpacing: '1px' }}>
        {publisher.toUpperCase()} // {new Date(createdTime).toLocaleString()}
      </div>

      <h3 className="card-title">{title}</h3>
      
      {summary && (
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '20px', lineBreak: 'anywhere' }}>
          {summary}
        </p>
      )}

      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '24px' }}>
        <div style={{ flex: 1, height: '4px', background: 'rgba(255,255,255,0.05)', borderRadius: '2px', overflow: 'hidden' }}>
          <div style={{ width: `${score}%`, height: '100%', background: isVerified ? 'var(--c-green)' : 'var(--c-cyan)', boxShadow: isVerified ? '0 0 10px var(--c-green)' : '0 0 10px var(--c-cyan)' }} />
        </div>
        <span style={{ fontSize: '0.9rem', fontWeight: 900, color: isVerified ? 'var(--c-green)' : 'var(--c-cyan)', fontFamily: 'var(--font-data)' }}>
          {score.toFixed(0)}%
        </span>
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', paddingTop: '16px', borderTop: '1px solid var(--color-border)', gap: '12px' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
          {isRecycleBin ? (
            <button className="btn btn-ghost" style={{ height: '32px', padding: '0 12px', fontSize: '0.65rem' }} onClick={handleRestore}>
              <RotateCcw size={12} /> RESTORE
            </button>
          ) : (
            <>
              {status === 'Draft' && (
                <>
                  <button className="btn btn-primary" style={{ height: '32px', padding: '0 12px', fontSize: '0.65rem', background: 'var(--c-green)', color: '#000' }} onClick={handleApprove}>
                    <Star size={12} /> APPROVE
                  </button>
                  <button className="btn btn-primary" style={{ height: '32px', padding: '0 12px', fontSize: '0.65rem', marginLeft: '8px' }} onClick={handlePublish}>
                    <ExternalLink size={12} /> PUBLISH
                  </button>
                </>
              )}
              {status === 'Approved' && (
                <button className="btn btn-primary" style={{ height: '32px', padding: '0 12px', fontSize: '0.65rem' }} onClick={handlePublish}>
                  <ExternalLink size={12} /> PUBLISH
                </button>
              )}
              {status !== 'Published' && (
                <button className="btn btn-ghost" style={{ height: '32px', padding: '0 12px', fontSize: '0.65rem', color: 'var(--c-magenta)' }} onClick={handleReject}>
                  <Trash2 size={12} /> REJECT
                </button>
              )}
              {status === 'Published' && (
                <>
                  <span className="badge badge-cyan" style={{ border: 'none', background: 'rgba(0,240,255,0.05)' }}>LIVE ON PORTAL</span>
                  <button className="btn btn-ghost" style={{ height: '32px', padding: '0 12px', fontSize: '0.65rem', marginLeft: '8px' }} onClick={handleRevertToDraft}>
                    <RotateCcw size={12} /> REVERT TO DRAFT
                  </button>
                </>
              )}
            </>
          )}
        </div>
        <ExternalLink size={14} style={{ opacity: 0.3 }} />
      </div>
    </div>
  )
}

export default function NewsBoard({ isRecycleBin }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { searchQuery, statusFilter, isOrchestrating } = useStore()
  
  const { data: res, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['news', isRecycleBin, searchQuery, statusFilter],
    queryFn: () => isRecycleBin ? NewsService.getRejected() : NewsService.getNews({ 
      search: searchQuery, 
      status: statusFilter === 'All' ? '' : statusFilter,
      limit: 1000
    }),
    refetchInterval: 30000, 
  })

  const mutation = useMutation({
    mutationFn: ({ action, id, params }) => {
      if (action === 'restore') return NewsService.restoreArticle(id)
      return NewsService.performAction(action, id, params)
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['news'])
    }
  })

  const items = Array.isArray(res) ? res : (res?.items || [])

  const columns = useMemo(() => {
    if (isRecycleBin) return { 'Rejected': items }
    
    // Define the canonical order of columns — no "In Review" column
    const base = {
      'Draft':     [],
      'Approved':  [],
      'Published': []
    }

    // Distribute items into columns
    items.forEach(item => {
      const f = item.fields || item
      let s = f.status || f.Status || item.status || 'Draft'

      // Remap any legacy "In Review" items directly into Approved
      if (s === 'In Review') s = 'Approved'
        
      // Drafts section should only show news fetched in the last 48 hours
      if (s === 'Draft') {
        const createdStr = f.created_at || item.created_at || item.createdTime || f.createdTime;
        if (createdStr) {
          let parseStr = createdStr.replace(' ', 'T');
          if (!parseStr.includes('Z') && !parseStr.includes('+') && !parseStr.includes('-')) {
            parseStr += 'Z';
          }
          const createdDate = new Date(parseStr);
          const now = new Date();
          const hoursDiff = (now - createdDate) / (1000 * 60 * 60);
          if (hoursDiff > 48) {
            return; // Skip rendering this draft
          }
        }
      }

      if (base[s]) {
        base[s].push(item)
      } else {
        // Fallback for unexpected status
        if (!base[s]) base[s] = []
        base[s].push(item)
      }
    })

    // If a specific filter is set, filter out other statuses but keep the column mapping intact
    if (statusFilter && statusFilter !== 'All') {
      const filtered = {}
      Object.keys(base).forEach(col => {
        if (col === statusFilter) {
          filtered[col] = base[col]
        }
      })
      return filtered
    }
    
    return base
  }, [items, isRecycleBin, statusFilter])

  if (isLoading) return <Loader message="ACCESSING NEWS MATRIX..." />
  if (isError) return <ErrorState error={error.message} />
  
  const totalItems = items.length
  // Check if any of the columns have items to show
  const hasVisibleItems = Object.values(columns).some(col => col.length > 0)
  if (!hasVisibleItems) {
    if (isOrchestrating) {
      return <Loader message="ORCHESTRATING INGESTION PIPELINE... SCAPING & PROCESSING INDIAN EV NEWS..." />
    }
    return <EmptyState title={isRecycleBin ? "RECYCLE BIN EMPTY" : "NO SIGNALS FOUND"} subtitle="START PIPELINE TO INGEST INTELLIGENCE" />
  }

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h2 style={{ color: 'var(--c-cyan)', fontWeight: 900, letterSpacing: '1px' }}>
            {isRecycleBin ? 'RECYCLE BIN' : 'EDITORIAL KANBAN'}
          </h2>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 800, marginTop: '4px' }}>
            {statusFilter && statusFilter !== 'All' && !isRecycleBin ? `FILTERED BY ${statusFilter.toUpperCase()}` : 'FULL SYSTEM OVERVIEW'}
            <span style={{ marginLeft: '12px', color: 'var(--c-cyan)' }}>{totalItems} TOTAL SIGNALS</span>
          </div>
        </div>
        <button className="btn btn-ghost" onClick={() => refetch()}>
          <RefreshCw size={14} style={{ marginRight: '8px' }} /> REFRESH
        </button>
      </div>
      
      {isOrchestrating && (
        <div style={{
          background: 'rgba(255, 0, 128, 0.1)',
          border: '1px solid var(--c-magenta)',
          color: 'var(--c-magenta)',
          padding: '12px 16px',
          borderRadius: '4px',
          marginBottom: '24px',
          fontSize: '0.8rem',
          fontWeight: 800,
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          fontFamily: 'var(--font-data)',
          letterSpacing: '1px',
          boxShadow: '0 0 10px rgba(255, 0, 128, 0.15)'
        }}>
          <span style={{ fontSize: '1.2rem', animation: 'spin 2s linear infinite' }}>⏳</span>
          <span>INGESTION PIPELINE RUNNING: SCRAPING & REWRITING INDIAN EV NEWS IN BACKGROUND (DRAFTS REFRESHING DYNAMICALLY...)</span>
        </div>
      )}
      
      <div className="kanban-board" style={{ 
        display: 'flex', 
        gap: '24px', 
        overflowX: 'auto', 
        paddingBottom: '20px',
        alignItems: 'flex-start'
      }}>
        {Object.entries(columns).map(([name, colItems]) => (
          <div key={name} className="kanban-column" style={{ 
            minWidth: '350px', 
            flex: (statusFilter && statusFilter !== 'All') ? '0 0 450px' : '0 0 350px',
            maxHeight: 'calc(100vh - 180px)'
          }}>
            <div className="column-header">
              <span>{name}</span>
              <span style={{ opacity: 0.5, background: 'rgba(255,255,255,0.1)', padding: '2px 10px', borderRadius: '12px', fontSize: '0.7rem' }}>{colItems.length}</span>
            </div>
            <div className="column-content" style={{ overflowY: 'auto' }}>
              {colItems.map(item => (
                <ArticleCard 
                  key={item.id} 
                  item={item} 
                  isRecycleBin={isRecycleBin}
                  onClick={() => navigate(`/article/${item.id}`)} 
                  onReject={(id) => mutation.mutate({ action: 'reject_article', id })}
                  onRestore={(id) => mutation.mutate({ action: 'restore', id })}
                  onAction={(action, id) => mutation.mutate({ action, id })}
                />
              ))}
              {colItems.length === 0 && (
                <div style={{ padding: '60px 20px', textAlign: 'center', opacity: 0.3, fontSize: '0.75rem', border: '1px dashed var(--color-border)', borderRadius: '12px', margin: '10px' }}>
                  NO {name.toUpperCase()} DATA FOUND
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}


