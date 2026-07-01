import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { API_BASE } from '../store'

// --- REUSABLE UTILS ---

async function fetchApi(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, options)
  const json = await res.json()
  if (!json.success) throw new Error(json.error || 'API Error')
  return json.data
}

function Loader({ message }) {
  return (
    <div className="flex-center" style={{ height: '100%', flexDirection: 'column' }}>
      <div className="loader-spinner"></div>
      <div style={{ marginTop: '20px', fontSize: '0.7rem', fontWeight: 800, color: 'var(--text-muted)' }}>{message}</div>
    </div>
  )
}

function EmptyState({ title, subtitle = "NO DATA AVAILABLE" }) {
  return (
    <div className="flex-center" style={{ height: '100%', flexDirection: 'column', textAlign: 'center', padding: '40px' }}>
      <div style={{ fontSize: '3rem', marginBottom: '20px', opacity: 0.5 }}>📁</div>
      <div style={{ fontWeight: 900, color: '#fff', fontSize: '1.2rem', marginBottom: '8px' }}>{title}</div>
      <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem', letterSpacing: '1px' }}>{subtitle.toUpperCase()}</div>
    </div>
  )
}

// --- MODULE PAGES ---

export function SourceLearningView() {
  const { data, isLoading, isError } = useQuery({ 
    queryKey: ['sources'], 
    queryFn: () => fetchApi('/api/sources')
  })

  if (isLoading) return <Loader message="SYNCHRONIZING SOURCE KNOWLEDGE..." />
  if (isError || !data || data.length === 0) return <EmptyState title="NO SOURCES LOADED" />

  return (
    <div className="module-page">
      <div className="module-header">
        <h2 style={{ color: 'var(--c-cyan)', fontWeight: 900 }}>🧠 SOURCE LEARNING ENGINE</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Monitoring authority and accuracy of EV source nodes.</p>
      </div>
      
      <div className="module-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '20px' }}>
        {data.map(s => (
          <div key={s.source_id} className="control-block highlight-hover">
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '15px' }}>
              <div>
                <div className="block-title">{s.name}</div>
                <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>{s.domain}</div>
              </div>
              <div style={{ fontSize: '1.5rem', color: 'var(--c-cyan)', fontWeight: 900 }}>{(s.final_score * 100).toFixed(0)}</div>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem' }}>
              <span className="badge badge-outline">{s.type?.toUpperCase()}</span>
              <span style={{ color: 'var(--c-green)' }}>{s.activity_status?.toUpperCase()}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export function GrowthEngineView() {
  const navigate = useNavigate()
  const { data, isLoading, isError } = useQuery({ 
    queryKey: ['growth-engine'], 
    queryFn: () => fetchApi('/api/growth')
  })

  if (isLoading) return <Loader message="CALCULATING GROWTH VELOCITY..." />
  if (isError || !data?.top_signals?.length) return <EmptyState title="NO GROWTH SIGNALS FOUND" />

  return (
    <div className="module-page">
      <div className="module-header">
        <h2 style={{ color: 'var(--c-magenta)', fontWeight: 900 }}>📈 GROWTH FLYWHEEL</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Ranking top performing EV intelligence signals by growth velocity.</p>
      </div>

      <div className="module-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', gap: '20px' }}>
        {data.top_signals.map(s => (
          <div key={s.id} className="control-block highlight-hover" onClick={() => navigate(`/article/${s.id}`)} style={{ cursor: 'pointer' }}>
            <div className="block-title">{s.title}</div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginTop: '20px' }}>
              <div>
                <div style={{ fontSize: '1.5rem', fontWeight: 900, color: '#fff' }}>{(s.traffic_total || 0).toLocaleString()}</div>
                <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)' }}>TOTAL VIEWS</div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '1.5rem', fontWeight: 900, color: 'var(--c-magenta)' }}>{(s.growth_score || 0).toFixed(1)}</div>
                <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)' }}>GROWTH SCORE</div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export function AnalyticsView() {
  const navigate = useNavigate()
  const { data, isLoading, isError } = useQuery({ 
    queryKey: ['global-analytics'], 
    queryFn: () => fetchApi('/api/analytics')
  })

  if (isLoading) return <Loader message="COMPILING ANALYTICS MATRIX..." />
  if (isError || !data) return <EmptyState title="NO ANALYTICS DATA" />

  return (
    <div className="module-page">
      <div className="module-header">
        <h2 style={{ color: 'var(--c-cyan)', fontWeight: 900 }}>📊 PERFORMANCE ANALYTICS</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Aggregated performance metrics across the EV intelligence network.</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px', marginBottom: '40px' }}>
        <div className="control-block">
          <div className="block-title">TOTAL NETWORK VIEWS</div>
          <div style={{ fontSize: '2.5rem', fontWeight: 900, color: '#fff' }}>{(data.total_views || 0).toLocaleString()}</div>
        </div>
        <div className="control-block">
          <div className="block-title">AVERAGE CTR</div>
          <div style={{ fontSize: '2.5rem', fontWeight: 900, color: 'var(--c-green)' }}>{(data.avg_ctr || 0).toFixed(2)}%</div>
        </div>
        <div className="control-block">
          <div className="block-title">TREND VELOCITY</div>
          <div style={{ fontSize: '2.5rem', fontWeight: 900, color: 'var(--c-cyan)' }}>+14.2%</div>
        </div>
      </div>

      <div className="control-block" style={{ marginBottom: '40px' }}>
        <div className="block-title">NETWORK TRAFFIC (LAST 7 DAYS)</div>
        <div style={{ height: '150px', display: 'flex', alignItems: 'flex-end', gap: '10px', padding: '10px 0' }}>
          {data.time_series?.map((v, i) => (
            <div key={i} style={{ flex: 1, background: 'var(--c-cyan)', height: `${(v/Math.max(...data.time_series, 1))*100}%`, borderRadius: '4px', transition: 'height 0.3s ease' }} />
          ))}
        </div>
      </div>

      <div className="control-block">
        <div className="block-title">TOP ARTICLES BY ENGAGEMENT</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '20px' }}>
          {data.top_articles?.map(a => (
            <div key={a.id} className="news-card" onClick={() => navigate(`/article/${a.id}`)} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ fontWeight: 700 }}>{a.title}</div>
              <div style={{ fontSize: '0.8rem', color: 'var(--c-cyan)' }}>{a.traffic_total} views</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export function GroqUsageView() {
  const { data, isLoading, isError } = useQuery({ 
    queryKey: ['groq-usage'], 
    queryFn: () => fetchApi('/api/groq-usage')
  })

  if (isLoading) return <Loader message="CHECKING LLM ALLOCATION..." />
  if (isError || !data) return <EmptyState title="USAGE DATA UNAVAILABLE" />

  return (
    <div className="module-page">
      <div className="module-header">
        <h2 style={{ color: 'var(--c-magenta)', fontWeight: 900 }}>⚡ LLM RESOURCE USAGE</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Real-time monitoring of autonomous processing resources.</p>
      </div>

      <div className="control-block" style={{ maxWidth: '600px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '20px' }}>
          <div className="block-title">DAILY TOKEN LIMIT</div>
          <div style={{ color: 'var(--c-magenta)', fontWeight: 900 }}>{(data.percentage || 0).toFixed(1)}% CONSUMED</div>
        </div>
        <div className="score-meter" style={{ height: '16px', marginBottom: '30px' }}>
          <div className="score-fill" style={{ width: `${data.percentage}%`, background: 'var(--c-magenta)', transition: 'width 0.5s ease' }} />
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '40px' }}>
          <div>
            <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginBottom: '5px' }}>USED TOKENS</div>
            <div style={{ fontSize: '1.8rem', fontWeight: 900 }}>{(data.used || 0).toLocaleString()}</div>
          </div>
          <div>
            <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginBottom: '5px' }}>REMAINING</div>
            <div style={{ fontSize: '1.8rem', fontWeight: 900 }}>{((data.limit || 0) - (data.used || 0)).toLocaleString()}</div>
          </div>
        </div>
      </div>
    </div>
  )
}

export function SEOStrategyView() {
  const { data, isLoading, isError } = useQuery({ 
    queryKey: ['seo-strategy'], 
    queryFn: () => fetchApi('/api/seo')
  })

  if (isLoading) return <Loader message="MAPPING KEYWORD CLUSTERS..." />
  if (isError || !data?.keywords?.length) return <EmptyState title="NO SEO DATA AVAILABLE" />

  return (
    <div className="module-page">
      <div className="module-header">
        <h2 style={{ color: 'var(--c-green)', fontWeight: 900 }}>🌐 SEO INTELLIGENCE</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Automated keyword tracking and ranking analytics.</p>
      </div>

      <div className="control-block">
        <div className="block-title">KEYWORD PERFORMANCE MATRIX</div>
        <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '20px' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--color-border)', textAlign: 'left' }}>
              <th style={{ padding: '10px', fontSize: '0.65rem', color: 'var(--text-muted)' }}>TERM</th>
              <th style={{ padding: '10px', fontSize: '0.65rem', color: 'var(--text-muted)' }}>RANK</th>
              <th style={{ padding: '10px', fontSize: '0.65rem', color: 'var(--text-muted)' }}>IMPRESSIONS</th>
            </tr>
          </thead>
          <tbody>
            {data.keywords.map((k, i) => (
              <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                <td style={{ padding: '15px 10px', fontWeight: 700 }}>{k.term}</td>
                <td style={{ padding: '15px 10px', color: 'var(--c-green)', fontWeight: 800 }}>#{k.rank}</td>
                <td style={{ padding: '15px 10px', color: 'var(--text-secondary)' }}>{(k.impressions || 0).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export function SocialBundleView() {
  return (
    <div className="module-page flex-center" style={{ textAlign: 'center' }}>
      <div>
        <div style={{ fontSize: '4rem', marginBottom: '20px' }}>📱</div>
        <h2 style={{ fontWeight: 900, color: '#fff', marginBottom: '10px' }}>SOCIAL PIPELINE ACTIVE</h2>
        <p style={{ color: 'var(--text-muted)', letterSpacing: '1px' }}>SOCIAL BUNDLES ARE GENERATED AUTOMATICALLY PER ARTICLE VIEW.</p>
      </div>
    </div>
  )
}

export function ExperimentsView() {
  const navigate = useNavigate()
  const { data, isLoading, isError } = useQuery({ 
    queryKey: ['experiments'], 
    queryFn: () => fetchApi('/api/experiments')
  })

  if (isLoading) return <Loader message="SYNCING BANDIT LAB..." />
  if (isError || !data || data.length === 0) return <EmptyState title="NO ACTIVE EXPERIMENTS" />

  return (
    <div className="module-page">
      <div className="module-header">
        <h2 style={{ color: 'var(--c-magenta)', fontWeight: 900 }}>🔬 MULTI-ARMED BANDIT LAB</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Live A/B testing of headlines and thumbnails across the matrix.</p>
      </div>

      <div className="module-grid" style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '30px' }}>
        {data.map(exp => (
          <div key={exp.article_id} className="control-block highlight-hover" onClick={() => navigate(`/article/${exp.article_id}`)} style={{ cursor: 'pointer' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '20px' }}>
              <div className="block-title">{exp.title}</div>
              <div className="badge badge-magenta">ACTIVE TEST</div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '20px' }}>
              {exp.variants.map((v, i) => (
                <div key={i} style={{ padding: '20px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: v.text === exp.winner ? '1px solid var(--c-green)' : '1px solid transparent' }}>
                  <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)', marginBottom: '10px' }}>VARIANT {i+1}</div>
                  <div style={{ fontSize: '1rem', fontWeight: 700, color: '#fff', marginBottom: '10px' }}>{v.text}</div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 900, color: 'var(--c-magenta)' }}>{v.ctr.toFixed(2)}% CTR</div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

