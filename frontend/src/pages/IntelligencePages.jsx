import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { Globe, Cpu, RefreshCw } from 'lucide-react'
import { AnalyticsService, IntelligenceService } from '../services/api'
import { Loader, EmptyState, ErrorState } from '../components/StatusStates'

/* ─── SOURCE LEARNING ────────────────────────────────────────── */
export function SourceLearningView() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['sources'],
    queryFn: () => IntelligenceService.getSources()
  })

  if (isLoading) return <Loader message="SYNCHRONIZING SOURCE KNOWLEDGE..." />
  if (isError) return <ErrorState error={error.message} />
  if (!data?.length) return <EmptyState title="NO SOURCES LOADED" />

  return (
    <div className="module-page" style={{ padding: '40px' }}>
      <div className="module-header" style={{ marginBottom: '40px' }}>
        <h2 style={{ color: 'var(--c-cyan)', fontWeight: 900, display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Globe /> SOURCE LEARNING ENGINE
        </h2>
      </div>
      <div className="control-block">
        <table className="full" style={{ borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--color-border)', color: 'var(--text-muted)', fontSize: '0.7rem' }}>
              <th style={{ padding: '12px' }}>SOURCE NAME</th>
              <th style={{ padding: '12px' }}>TYPE</th>
              <th style={{ padding: '12px' }}>TRUST SCORE</th>
              <th style={{ padding: '12px' }}>LAST UPDATED</th>
            </tr>
          </thead>
          <tbody>
            {data.map(s => (
              <tr key={s.id} style={{ borderBottom: '1px solid var(--color-border)', fontSize: '0.85rem' }}>
                <td style={{ padding: '16px 12px', fontWeight: 700, color: 'var(--c-cyan)' }}>{s.name}</td>
                <td style={{ padding: '16px 12px' }}>
                   <span className="badge badge-outline">{s.type || 'Media'}</span>
                </td>
                <td style={{ padding: '16px 12px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <div style={{ width: '60px', height: '4px', background: 'rgba(255,255,255,0.1)' }}>
                       <div style={{ width: `${s.final_score * 100}%`, height: '100%', background: 'var(--c-cyan)' }} />
                    </div>
                    {(s.final_score * 100).toFixed(0)}
                  </div>
                </td>
                <td style={{ padding: '16px 12px', opacity: 0.6 }}>{s.last_updated || 'RECENT'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

/* ─── GROQ USAGE ─────────────────────────────────────────────── */
export function GroqUsageView() {
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['groq-usage'],
    queryFn: () => AnalyticsService.getGroq()
  })

  if (isLoading) return <Loader message="CHECKING LLM ALLOCATION..." />
  if (isError) return <ErrorState error={error.message} />
  if (!data) return <EmptyState title="USAGE DATA UNAVAILABLE" />

  return (
    <div className="module-page" style={{ padding: '40px' }}>
      <div className="module-header" style={{ marginBottom: '40px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 style={{ color: 'var(--c-magenta)', fontWeight: 900, display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Cpu /> LLM RESOURCE USAGE
        </h2>
        <button className="btn btn-ghost" onClick={() => refetch()}>
          <RefreshCw size={14} style={{ marginRight: '8px' }} /> REFRESH
        </button>
      </div>
      <div className="control-block" style={{ maxWidth: '800px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '20px' }}>
           <div>
             <div className="block-title">TOKENS CONSUMED</div>
             <div style={{ fontSize: '2.5rem', fontWeight: 900 }}>{data.used.toLocaleString()}</div>
           </div>
           <div style={{ textAlign: 'right' }}>
             <div className="block-title">LIMIT ALLOCATION</div>
             <div style={{ fontSize: '2.5rem', fontWeight: 900, opacity: 0.3 }}>{data.limit.toLocaleString()}</div>
           </div>
        </div>
        <div className="score-meter" style={{ height: '24px', borderRadius: '12px' }}>
          <div className="score-fill" style={{ width: `${data.percentage}%`, background: 'linear-gradient(90deg, var(--c-cyan), var(--c-magenta))' }} />
        </div>
        <div style={{ marginTop: '12px', textAlign: 'center', fontWeight: 900, color: 'var(--c-magenta)' }}>
           {data.percentage.toFixed(2)}% CAPACITY UTILIZED
        </div>
      </div>
    </div>
  )
}
