import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts'
import { TrendingUp, Globe, Search, Share2, Beaker, Cpu, BarChart2, Zap, Clock, ExternalLink, RefreshCw, X } from 'lucide-react'
import { AnalyticsService, IntelligenceService, NewsService } from '../services/api'
import { Loader, EmptyState, ErrorState } from '../components/StatusStates'

/* ─── ANALYTICS VIEW ────────────────────────────────────────── */
export function AnalyticsView() {
  const navigate = useNavigate()
  const { data, isLoading, isError, error } = useQuery({ 
    queryKey: ['analytics'], 
    queryFn: () => AnalyticsService.getStats() 
  })

  if (isLoading) return <Loader message="COMPILING ANALYTICS MATRIX..." />
  if (isError) return <ErrorState error={error.message} />
  if (!data?.top_articles?.length) return <EmptyState title="NO ANALYTICS DATA" />

  const chartData = data.time_series.map((val, i) => ({ day: i + 1, views: val }))

  return (
    <div className="module-page" style={{ padding: '40px' }}>
      <div className="module-header" style={{ marginBottom: '40px' }}>
        <h2 style={{ color: 'var(--c-cyan)', fontWeight: 900, display: 'flex', alignItems: 'center', gap: '12px' }}>
          <BarChart2 /> PERFORMANCE ANALYTICS
        </h2>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px', marginBottom: '40px' }}>
        <div className="control-block">
          <div className="block-title">TOTAL NETWORK VIEWS</div>
          <div style={{ fontSize: '2.5rem', fontWeight: 900 }}>{data.total_views.toLocaleString()}</div>
        </div>
        <div className="control-block">
          <div className="block-title">AVG CLICK-THROUGH RATE</div>
          <div style={{ fontSize: '2.5rem', fontWeight: 900, color: 'var(--c-green)' }}>{data.avg_ctr.toFixed(2)}%</div>
        </div>
        <div className="control-block">
          <div className="block-title">AVG ENGAGEMENT</div>
          <div style={{ fontSize: '2.5rem', fontWeight: 900, color: 'var(--c-magenta)' }}>8.4%</div>
        </div>
      </div>

      <div className="control-block" style={{ marginBottom: '40px', height: '300px' }}>
        <div className="block-title">TRAFFIC TIMELINE (7D)</div>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="day" stroke="var(--text-muted)" />
            <YAxis stroke="var(--text-muted)" />
            <Tooltip contentStyle={{ background: 'var(--color-panel)', border: '1px solid var(--color-border)' }} />
            <Line type="monotone" dataKey="views" stroke="var(--c-cyan)" strokeWidth={3} dot={{ fill: 'var(--c-cyan)' }} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="control-block">
        <div className="block-title">PUBLISHED ARTICLE PERFORMANCE</div>
        <table className="full" style={{ borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--color-border)', color: 'var(--text-muted)', fontSize: '0.7rem' }}>
              <th style={{ padding: '12px' }}>ARTICLE TITLE</th>
              <th style={{ padding: '12px' }}>VIEWS</th>
              <th style={{ padding: '12px' }}>CTR</th>
              <th style={{ padding: '12px' }}>ACTIONS</th>
            </tr>
          </thead>
          <tbody>
            {data.top_articles.map(a => (
              <tr key={a.id} style={{ borderBottom: '1px solid var(--color-border)', fontSize: '0.85rem' }}>
                <td style={{ padding: '16px 12px', maxWidth: '400px', fontWeight: 600 }}>{a.title}</td>
                <td style={{ padding: '16px 12px' }}>{a.traffic_total.toLocaleString()}</td>
                <td style={{ padding: '16px 12px', color: 'var(--c-green)' }}>{a.ctr_avg.toFixed(2)}%</td>
                <td style={{ padding: '16px 12px' }}>
                  <button className="btn btn-ghost" onClick={() => navigate(`/article/${a.id}`)}>VIEW</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

/* ─── GROWTH ENGINE ─────────────────────────────────────────── */
export function GrowthEngineView() {
  const navigate = useNavigate()
  const { data, isLoading, isError, error } = useQuery({ 
    queryKey: ['growth'], 
    queryFn: () => AnalyticsService.getGrowth() 
  })

  if (isLoading) return <Loader message="CALCULATING GROWTH VECTORS..." />
  if (isError) return <ErrorState error={error.message} />
  if (!data?.top_signals?.length) return <EmptyState title="NO GROWTH DATA" />

  return (
    <div className="module-page" style={{ padding: '40px' }}>
      <div className="module-header" style={{ marginBottom: '40px' }}>
        <h2 style={{ color: 'var(--c-green)', fontWeight: 900, display: 'flex', alignItems: 'center', gap: '12px' }}>
          <TrendingUp /> GROWTH ENGINE
        </h2>
      </div>

      <div className="module-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(400px, 1fr))', gap: '20px' }}>
        {data.top_signals.map((s, i) => (
          <div key={s.id} className="control-block highlight-hover" onClick={() => navigate(`/article/${s.id}`)}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
              <span className="badge badge-green">RANK #{i+1}</span>
              <span style={{ color: 'var(--c-cyan)', fontWeight: 900 }}>SCORE: {s.growth_score.toFixed(0)}</span>
            </div>
            <h3 style={{ marginBottom: '16px' }}>{s.title}</h3>
            <div style={{ display: 'flex', gap: '24px', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              <span>TRAFFIC: <strong style={{ color: '#fff' }}>{s.traffic_total}</strong></span>
              <span>CTR: <strong style={{ color: '#fff' }}>{s.ctr_avg.toFixed(2)}%</strong></span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ─── SEO STRATEGY ─────────────────────────────────────────── */
export function SEOMatrixView() {
  const navigate = useNavigate()
  const { data, isLoading, isError, error } = useQuery({ 
    queryKey: ['seo'], 
    queryFn: () => AnalyticsService.getSEO() 
  })

  if (isLoading) return <Loader message="SCANNING SEARCH LANDSCAPE..." />
  if (isError) return <ErrorState error={error.message} />
  if (!data?.keywords?.length) return <EmptyState title="NO SEO DATA" />

  return (
    <div className="module-page" style={{ padding: '40px' }}>
      <div className="module-header" style={{ marginBottom: '40px' }}>
        <h2 style={{ color: 'var(--c-cyan)', fontWeight: 900, display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Search /> SEO STRATEGY MATRIX
        </h2>
      </div>

      <div className="control-block" style={{ marginBottom: '30px', height: '200px' }}>
        <div className="block-title">NETWORK TRAFFIC TRENDS</div>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data.timeline.map((v, i) => ({ i, v }))}>
            <Bar dataKey="v" fill="var(--c-cyan)" opacity={0.5} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="control-block">
        <div className="block-title">KEYWORD RANKINGS</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '16px' }}>
          {data.keywords.map((k, i) => (
            <div key={i} className="control-block" style={{ background: 'rgba(255,255,255,0.02)', padding: '16px', cursor: 'pointer' }} onClick={() => navigate(`/article/${k.article_id}`)}>
              <div style={{ fontSize: '1rem', fontWeight: 800, marginBottom: '8px', color: 'var(--c-cyan)' }}>{k.keyword}</div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', opacity: 0.7 }}>
                <span>RANK: #{k.rank}</span>
                <span>TRAFFIC: {k.traffic}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

/* ─── SOCIAL MODAL HELPER ───────────────────────────────────── */
function SocialModal({ isOpen, onClose, bundle }) {
  const [activeTab, setActiveTab] = useState('twitter')
  const [copied, setCopied] = useState(false)

  if (!isOpen || !bundle) return null

  const twitterText = bundle.tweet?.text || bundle.tweet || ''
  const linkedinText = bundle.linkedin?.body || bundle.linkedin?.text || bundle.linkedin || ''

  const handleCopy = () => {
    const textToCopy = activeTab === 'twitter' ? twitterText : linkedinText
    navigator.clipboard.writeText(textToCopy)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-container" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>⚡ VIRAL SOCIAL BUNDLE</h3>
          <button className="modal-close-btn" onClick={onClose}>
            <X size={20} />
          </button>
        </div>
        <div className="modal-content">
          <div className="modal-tabs">
            <button 
              className={`modal-tab ${activeTab === 'twitter' ? 'active' : ''}`}
              onClick={() => { setActiveTab('twitter'); setCopied(false); }}
            >
              X / TWITTER THREAD
            </button>
            <button 
              className={`modal-tab ${activeTab === 'linkedin' ? 'active' : ''}`}
              onClick={() => { setActiveTab('linkedin'); setCopied(false); }}
            >
              LINKEDIN ANALYSIS
            </button>
          </div>
          <div className="modal-tab-content">
            {activeTab === 'twitter' ? twitterText : linkedinText}
          </div>
        </div>
        <div className="modal-footer">
          <button className="btn btn-ghost" onClick={onClose}>CLOSE</button>
          <button className="btn btn-primary" onClick={handleCopy}>
            {copied ? 'COPIED!' : 'COPY TO CLIPBOARD'}
          </button>
        </div>
      </div>
    </div>
  )
}

/* ─── SOCIAL BUNDLE ─────────────────────────────────────────── */
export function SocialBundleView() {
  const [selectedId, setSelectedId] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [generatedBundle, setGeneratedBundle] = useState(null)
  const queryClient = useQueryClient()
  
  const { data: articles } = useQuery({ 
    queryKey: ['news-published'], 
    queryFn: () => NewsService.getNews({ status: 'Published' }) 
  })

  const { data: bundle, isLoading } = useQuery({ 
    queryKey: ['social-bundle', selectedId], 
    queryFn: () => IntelligenceService.getSocial(selectedId),
    enabled: !!selectedId
  })

  const mutation = useMutation({
    mutationFn: () => NewsService.performAction('generate_social', selectedId),
    onSuccess: (data) => {
      queryClient.invalidateQueries(['social-bundle', selectedId])
      if (data?.social_bundle) {
        setGeneratedBundle(data.social_bundle)
        setShowModal(true)
      }
    }
  })

  const items = articles?.items || []

  return (
    <div className="module-page" style={{ padding: '40px' }}>
      <div className="module-header" style={{ marginBottom: '40px' }}>
        <h2 style={{ color: 'var(--c-magenta)', fontWeight: 900, display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Share2 /> SOCIAL BUNDLE GENERATOR
        </h2>
      </div>

      <div className="control-block" style={{ marginBottom: '30px' }}>
        <div className="block-title">SELECT PUBLISHED ARTICLE</div>
        <select 
          className="full" 
          style={{ background: 'var(--color-panel)', border: '1px solid var(--color-border)', color: '#fff', padding: '12px', borderRadius: '8px', outline: 'none' }}
          value={selectedId}
          onChange={(e) => setSelectedId(e.target.value)}
        >
          <option value="">-- CHOOSE SIGNAL --</option>
          {items.map(a => <option key={a.id} value={a.id}>{a.fields.title}</option>)}
        </select>
      </div>

      {selectedId && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
          <div className="control-block">
            <div className="block-title">VIRAL TWEET</div>
            {isLoading ? <Loader /> : (
              <div style={{ background: 'rgba(0,0,0,0.2)', padding: '20px', borderRadius: '8px', fontSize: '0.95rem' }}>
                {bundle?.tweet?.text || "NOT GENERATED"}
              </div>
            )}
          </div>
          <div className="control-block">
            <div className="block-title">LINKEDIN POST</div>
            {isLoading ? <Loader /> : (
              <div style={{ background: 'rgba(0,0,0,0.2)', padding: '20px', borderRadius: '8px', fontSize: '0.95rem', whiteSpace: 'pre-wrap' }}>
                {bundle?.linkedin?.body || "NOT GENERATED"}
              </div>
            )}
          </div>
          <button className="btn btn-primary full" style={{ gridColumn: 'span 2' }} onClick={() => mutation.mutate()} disabled={mutation.isPending}>
            {mutation.isPending ? 'GENERATING...' : 'RE-GENERATE SOCIAL BUNDLE'}
          </button>
        </div>
      )}

      <SocialModal 
        isOpen={showModal} 
        onClose={() => setShowModal(false)} 
        bundle={generatedBundle} 
      />
    </div>
  )
}

/* ─── A/B EXPERIMENTS ────────────────────────────────────────── */
export function ExperimentsView() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data, isLoading, isError, error } = useQuery({ 
    queryKey: ['experiments'], 
    queryFn: () => AnalyticsService.getExperiments() 
  })

  const mutation = useMutation({
    mutationFn: ({ articleId, headline }) => NewsService.performAction('select_headline', articleId, { headline }),
    onSuccess: () => queryClient.invalidateQueries(['experiments'])
  })

  if (isLoading) return <Loader message="ANALYZING VARIANT PERFORMANCE..." />
  if (isError) return <ErrorState error={error.message} />
  if (!data?.length) return <EmptyState title="NO ACTIVE EXPERIMENTS" />

  return (
    <div className="module-page" style={{ padding: '40px' }}>
      <div className="module-header" style={{ marginBottom: '40px' }}>
        <h2 style={{ color: 'var(--c-yellow)', fontWeight: 900, display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Zap /> A/B EXPERIMENT LAB
        </h2>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        {data.map(exp => (
          <div key={exp.article_id} className="control-block">
            <div className="block-title" style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>ARTICLE: {exp.title}</span>
              <button className="btn btn-ghost" style={{ padding: '0 8px', fontSize: '0.6rem' }} onClick={() => navigate(`/article/${exp.article_id}`)}>VIEW ARTICLE</button>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              {exp.variants.map((v, i) => (
                <div key={i} style={{ padding: '16px', background: v.text === exp.winner ? 'rgba(0,255,157,0.05)' : 'rgba(255,255,255,0.02)', border: `1px solid ${v.text === exp.winner ? 'var(--c-green)' : 'var(--color-border)'}`, borderRadius: '8px' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '8px' }}>VARIANT {String.fromCharCode(65 + i)} {v.text === exp.winner && '(WINNER)'}</div>
                  <div style={{ fontSize: '0.9rem', marginBottom: '12px' }}>{v.text}</div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
                    <div style={{ flex: 1, height: '4px', background: 'rgba(255,255,255,0.1)', borderRadius: '2px' }}>
                      <div style={{ width: `${v.ctr * 10}%`, height: '100%', background: v.text === exp.winner ? 'var(--c-green)' : 'var(--c-cyan)', borderRadius: '2px' }} />
                    </div>
                    <span style={{ fontSize: '0.8rem', fontWeight: 900 }}>{v.ctr.toFixed(2)}% CTR</span>
                  </div>
                  {v.text !== exp.winner && (
                    <button className="btn btn-ghost full" style={{ fontSize: '0.7rem' }} onClick={() => mutation.mutate({ articleId: exp.article_id, headline: v.text })}>
                      SELECT AS WINNER
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

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
