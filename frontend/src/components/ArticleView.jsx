import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useStore, API_BASE } from '../store'

// --- SUB-COMPONENTS ---

function KeywordIntelligencePanel({ strategy, faqs }) {
  if (!strategy) return null
  let s = strategy
  let f = faqs
  try {
    if (typeof strategy === 'string') s = JSON.parse(strategy)
    if (typeof faqs === 'string') f = JSON.parse(faqs)
  } catch(e) {}

  return (
    <div className="control-block">
      <div className="block-title">Keyword Intelligence Strategy</div>
      <div style={{ marginBottom: '12px' }}>
        <div style={{ fontSize: '0.6rem', color: 'var(--c-cyan)', fontWeight: 800, marginBottom: '4px' }}>PRIMARY KEYWORD</div>
        <div style={{ fontSize: '0.85rem', color: '#fff', fontWeight: 600, background: 'rgba(0,240,255,0.05)', padding: '6px 10px', borderRadius: '4px' }}>{s.primary || 'Auto-Optimizing...'}</div>
      </div>
      
      <div style={{ marginBottom: '12px' }}>
        <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)', fontWeight: 800, marginBottom: '4px' }}>SECONDARY CLUSTERS</div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
          {s.secondary?.map((kw, i) => (
            <span key={i} style={{ fontSize: '0.65rem', background: 'rgba(255,255,255,0.03)', padding: '2px 8px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)' }}>{kw}</span>
          ))}
        </div>
      </div>

      {f && f.length > 0 && (
        <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px dashed var(--color-border)' }}>
          <div style={{ fontSize: '0.6rem', color: 'var(--c-green)', fontWeight: 800, marginBottom: '8px' }}>AUTO-GENERATED FAQs</div>
          {f.slice(0, 2).map((item, i) => (
            <div key={i} style={{ marginBottom: '8px' }}>
              <div style={{ fontSize: '0.7rem', color: '#fff', fontWeight: 600 }}>Q: {item.q}</div>
              <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>{item.a}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function SocialBundlePanel({ articleId, bundle }) {
  if (!bundle) return null
  const b = typeof bundle === 'string' ? JSON.parse(bundle) : bundle

  return (
    <div className="control-block">
      <div className="block-title">Social Viral Bundle</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {b.tweet && (
          <div style={{ padding: '8px', background: 'rgba(255,255,255,0.03)', borderRadius: '6px', fontSize: '0.75rem' }}>
            <div style={{ color: 'var(--c-cyan)', fontWeight: 800, fontSize: '0.6rem', marginBottom: '4px' }}>X (TWITTER) POST</div>
            <p style={{ color: 'var(--text-secondary)', lineHeight: 1.4 }}>{b.tweet.text}</p>
          </div>
        )}
        {b.linkedin && (
          <div style={{ padding: '8px', background: 'rgba(255,255,255,0.03)', borderRadius: '6px', fontSize: '0.75rem' }}>
            <div style={{ color: 'var(--c-blue)', fontWeight: 800, fontSize: '0.6rem', marginBottom: '4px' }}>LINKEDIN INSIGHT</div>
            <p style={{ color: 'var(--text-secondary)', lineHeight: 1.4, whiteSpace: 'pre-wrap' }}>{b.linkedin.body.substring(0, 150)}...</p>
          </div>
        )}
      </div>
    </div>
  )
}

function ContentScorePanel({ score, breakdown }) {
  if (!score) return null
  const b = typeof breakdown === 'string' ? JSON.parse(breakdown || '{}') : breakdown
  const items = [
    { label: 'Headline', val: b?.headline || 75 },
    { label: 'Topic', val: b?.topic || 80 },
    { label: 'Readability', val: b?.readability || 85 },
    { label: 'Source', val: b?.source || 90 },
    { label: 'Freshness', val: b?.freshness || 95 },
  ]

  return (
    <div className="control-block">
      <div className="block-title">Content Intelligence Score</div>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: '15px', marginBottom: '15px' }}>
        <div style={{ fontSize: '2.5rem', fontWeight: 900, color: 'var(--c-green)', lineHeight: 1 }}>{score.toFixed(0)}</div>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', paddingBottom: '5px' }}>TOTAL SCORE</div>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {items.map(i => (
          <div key={i.label}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', marginBottom: '2px' }}>
              <span style={{ color: 'var(--text-secondary)' }}>{i.label}</span>
              <span style={{ color: '#fff' }}>{i.val}%</span>
            </div>
            <div className="score-meter">
              <div className="score-fill" style={{ width: `${i.val}%`, background: 'var(--c-cyan)' }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function ArticleView() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { isEditMode, setEditMode } = useStore()
  const [isSplitView, setIsSplitView] = useState(false)
  const [editedArticle, setEditedArticle] = useState(null)
  const [activeActions, setActiveActions] = useState({}) // track loading per action
  const queryClient = useQueryClient()

  const { data: storyRes, isLoading, refetch } = useQuery({
    queryKey: ['article', id],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/api/news/${id}`)
      const json = await res.json()
      if (!json.success) throw new Error(json.error)
      setEditedArticle(json.data)
      return json.data
    },
    enabled: !!id
  })

  const { data: rawRes, isLoading: isRawLoading } = useQuery({
    queryKey: ['raw-source', id],
    queryFn: async () => {
        const res = await fetch(`${API_BASE}/api/action`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'get_raw_source', article_id: id })
        })
        const json = await res.json()
        return json.success ? json.data : { content: 'Error loading raw source: ' + json.error }
    },
    enabled: isSplitView && !!id
  })

  if (!id || isLoading || !storyRes) return (
    <div className="flex-center" style={{ height: '100%', color: 'var(--text-muted)' }}>LOADING ARTICLE INTELLIGENCE...</div>
  )

  const story = editedArticle || storyRes
  const sections = typeof story.sections === 'string' ? JSON.parse(story.sections || '[]') : story.sections
  const aiSummary = typeof story.ai_summary === 'string' ? JSON.parse(story.ai_summary || '{}') : story.ai_summary

  const handleAction = async (action, params = {}) => {
    if (activeActions[action]) return
    setActiveActions(prev => ({ ...prev, [action]: true }))

    try {
      const res = await fetch(`${API_BASE}/api/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, article_id: id, params })
      })
      const json = await res.json()

      if (json.success) {
        if (action === 'reject_article') {
            navigate('/news')
            queryClient.invalidateQueries(['news-kanban'])
        } else {
            // FIX: Manually fetch updated state to ensure UI reflects changes instantly
            const freshRes = await fetch(`${API_BASE}/api/news/${id}`)
            const freshJson = await freshRes.json()
            if (freshJson.success) {
                setEditedArticle(freshJson.data)
                // Also trigger react-query refetch to keep cache in sync
                queryClient.invalidateQueries(['article', id])
            }
            alert(`${action.replace('_', ' ').toUpperCase()} SUCCESSFUL`)
        }
      } else {
        alert(`ACTION FAILED: ${json.error}`)
      }
    } catch (e) {
      alert(`SYSTEM ERROR: ${e.message}`)
    } finally {
      setActiveActions(prev => ({ ...prev, [action]: false }))
    }
  }

  const handleFieldChange = (key, val) => {
    setEditedArticle(prev => ({ ...prev, [key]: val }))
  }

  const handleSectionChange = (index, field, val) => {
    const newSections = [...sections]
    newSections[index][field] = val
    handleFieldChange('sections', JSON.stringify(newSections))
  }

  const saveChanges = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/news/update?record_id=${id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editedArticle)
      })
      const json = await res.json()
      if (json.success) {
        setEditMode(false)
        queryClient.invalidateQueries(['news-kanban'])
        alert('CHANGES PERSISTED TO INTELLIGENCE CORE')
      } else {
          alert('SAVE FAILED: ' + json.error)
      }
    } catch (e) {
      alert('NETWORK ERROR: ' + e.message)
    }
  }

  return (
    <div className="intelligence-terminal">
      <div className="terminal-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <button className="btn btn-ghost" onClick={() => navigate(-1)}>← BACK</button>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className={`badge ${story.status === 'Published' ? 'badge-cyan' : 'badge-orange'}`}>{story.status}</span>
            <span style={{ fontSize: '0.8rem', fontWeight: 800 }}>SIGNAL ID: {id.substring(0, 8)}</span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {isEditMode && (
            <button className="btn btn-primary" style={{ background: 'var(--c-green)', color: '#000' }} onClick={saveChanges}>SAVE CHANGES</button>
          )}
          <div className={`edit-toggle ${isEditMode ? 'active' : ''}`} onClick={() => setEditMode(!isEditMode)}>
            {isEditMode ? '● EDITING' : '○ VIEW MODE'}
          </div>
          <button className="btn btn-ghost" onClick={() => setIsSplitView(!isSplitView)}>
            {isSplitView ? 'SINGLE VIEW' : 'SIDE-BY-SIDE'}
          </button>
          {story.status !== 'Rejected' && (
            <button 
                className="btn btn-primary" 
                onClick={() => handleAction('reject_article')} 
                disabled={activeActions['reject_article']}
                style={{ background: 'var(--c-magenta)' }}
            >
              {activeActions['reject_article'] ? 'REJECTING...' : 'REJECT'}
            </button>
          )}
          <button className="btn btn-primary">PUBLISH SIGNAL</button>
        </div>
      </div>

      <div className="terminal-body" style={{ height: 'calc(100vh - 120px)', overflow: 'hidden' }}>
        <div className="terminal-content" style={{ overflowY: 'auto', paddingRight: '20px' }}>
          {/* SEO META BLOCK ABOVE HEADLINE */}
          <div style={{ background: 'rgba(0, 240, 255, 0.03)', border: '1px dashed rgba(0, 240, 255, 0.2)', borderRadius: '8px', padding: '16px', marginBottom: '24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <span style={{ fontSize: '0.65rem', fontWeight: 800, color: 'var(--c-cyan)', letterSpacing: '1px' }}>SEO METADATA</span>
            </div>
            <div style={{ marginBottom: '8px' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)' }}>META TITLE: </span>
              {isEditMode ? (
                <input 
                  style={{ background: 'transparent', border: 'none', borderBottom: '1px dashed var(--color-border)', color: '#fff', width: '80%', outline: 'none', fontSize: '0.85rem' }}
                  value={story.meta_title || ''}
                  onChange={(e) => handleFieldChange('meta_title', e.target.value)}
                />
              ) : (
                <span style={{ fontSize: '0.85rem', color: '#fff' }}>{story.meta_title || 'Not generated'}</span>
              )}
            </div>
            <div>
              <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)' }}>META DESCRIPTION: </span>
              {isEditMode ? (
                <textarea 
                  style={{ background: 'transparent', border: 'none', borderBottom: '1px dashed var(--color-border)', color: '#fff', width: '80%', outline: 'none', fontSize: '0.85rem', resize: 'vertical' }}
                  value={story.meta_desc || ''}
                  onChange={(e) => handleFieldChange('meta_desc', e.target.value)}
                />
              ) : (
                <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{story.meta_desc || story.meta_description || 'Not generated'}</span>
              )}
            </div>
          </div>

          {isEditMode ? (
            <textarea 
              value={story.title || ""} 
              onChange={e => handleFieldChange('title', e.target.value)}
              style={{ width: '100%', background: 'rgba(0,240,255,0.03)', border: '1px solid var(--c-cyan)', color: '#fff', fontSize: '2rem', fontWeight: 900, padding: '12px', outline: 'none', borderRadius: '8px', marginBottom: '24px' }}
            />
          ) : (
            <h1 style={{ fontSize: '2.5rem', fontWeight: 900, marginBottom: '24px', lineHeight: 1.1 }}>{story.title || "Untitled"}</h1>
          )}

          {/* AI Summary Block */}
          <div style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid var(--color-border)', borderRadius: '12px', padding: '24px', marginBottom: '32px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ fontSize: '1.2rem' }}>⚡</span>
                <span style={{ fontSize: '0.8rem', fontWeight: 800, color: 'var(--c-cyan)', letterSpacing: '1px' }}>AI INTELLIGENCE SUMMARY</span>
              </div>
              <button 
                className="btn btn-ghost" 
                onClick={() => handleAction('generate_summary')} 
                disabled={activeActions['generate_summary']}
                style={{ fontSize: '0.6rem', padding: '2px 8px' }}
              >
                {activeActions['generate_summary'] ? 'PROCESSING...' : 'RE-SUMMARIZE'}
              </button>
            </div>
            {aiSummary ? (
              <>
                <h4 style={{ fontSize: '1.1rem', marginBottom: '12px', color: 'var(--c-cyan)' }}>{aiSummary.headline}</h4>
                <p style={{ fontSize: '1rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>{aiSummary.summary}</p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                  {(aiSummary.key_points || []).map((kp, i) => (
                    <div key={i} style={{ background: 'rgba(0,240,255,0.05)', padding: '4px 12px', borderRadius: '20px', fontSize: '0.8rem', border: '1px solid rgba(0,240,255,0.1)' }}>
                      • {typeof kp === 'object' ? (kp.fact || '') : kp}
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div style={{ color: 'var(--text-muted)' }}>Awaiting summary generation...</div>
            )}
          </div>

          <div style={{ display: isSplitView ? 'grid' : 'block', gridTemplateColumns: '1fr 1fr', gap: '32px' }}>
            <div style={{ overflowY: 'auto' }}>
              <div style={{ fontSize: '0.65rem', color: 'var(--c-cyan)', fontWeight: 800, marginBottom: '16px', display: 'flex', justifyContent: 'space-between' }}>
                <span>OPTIMIZED CONTENT</span>
                <button className="btn btn-ghost" style={{ fontSize: '0.6rem' }} onClick={() => handleAction('regenerate_headlines')}>REGEN HEADLINES</button>
              </div>
              {(sections || []).map((s, i) => (
                <div key={i} style={{ marginBottom: '24px' }}>
                  {isEditMode ? (
                      <>
                        <input 
                            value={s.heading || ''} 
                            onChange={e => handleSectionChange(i, 'heading', e.target.value)}
                            style={{ width: '100%', background: 'transparent', border: 'none', borderBottom: '1px solid var(--c-cyan)', color: '#fff', fontSize: '1.1rem', fontWeight: 800, marginBottom: '8px', padding: '4px' }}
                        />
                        <textarea 
                            value={typeof s.content === 'object' ? JSON.stringify(s.content) : (s.content || '')} 
                            onChange={e => handleSectionChange(i, 'content', e.target.value)}
                            style={{ width: '100%', background: 'rgba(255,255,255,0.02)', border: 'none', color: 'var(--text-secondary)', fontSize: '0.95rem', lineHeight: 1.6, padding: '8px', minHeight: '100px' }}
                        />
                      </>
                  ) : (
                      <>
                        <h3 style={{ fontSize: '1.1rem', fontWeight: 800, marginBottom: '8px', color: '#fff' }}>{s.heading || "Sub-Intelligence"}</h3>
                        {Array.isArray(s.content) ? (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                            {s.content.map((item, idx) => (
                              <p key={idx} style={{ fontSize: '0.95rem', color: 'var(--text-secondary)', lineHeight: 1.6, margin: 0 }}>
                                {typeof item === 'object' ? item.fact : item}
                              </p>
                            ))}
                          </div>
                        ) : (
                          <p style={{ fontSize: '0.95rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                            {typeof s.content === 'object' ? (s.content?.fact || '') : (s.content || "No detailed content provided.")}
                          </p>
                        )}
                      </>
                  )}
                </div>
              ))}
            </div>
            
            {isSplitView && (
              <div style={{ borderLeft: '1px solid var(--color-border)', flex: '0 0 50%', background: '#fff', display: 'flex', flexDirection: 'column', padding: 0 }}>
                <div style={{ margin: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.65rem', color: '#000', fontWeight: 800 }}>ORIGINAL SOURCE SIGNAL</span>
                  <a 
                    href={story.url} 
                    target="_blank" 
                    rel="noreferrer" 
                    className="btn btn-ghost" 
                    style={{ fontSize: '0.75rem', padding: '4px 10px', color: 'var(--c-cyan)', background: '#000', border: '1px solid var(--c-cyan)' }}
                  >
                    OPEN IN NEW TAB ↗
                  </a>
                </div>
                {story.url ? (
                  <iframe 
                    src={story.url} 
                    title="Original Source Signal" 
                    style={{ width: '100%', flex: 1, border: 'none', background: '#fff' }} 
                  />
                ) : (
                  <div style={{ padding: '20px', color: '#000' }}>No source URL available.</div>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="terminal-sidebar" style={{ overflowY: 'auto' }}>
          <ContentScorePanel 
            score={story.final_score || 0} 
            breakdown={story.score_breakdown} 
          />
          
          <KeywordIntelligencePanel strategy={story.seo_strategy} faqs={story.seo_faq} />

          <div style={{ marginBottom: '20px', display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '0.6rem', fontWeight: 800 }}>SOCIAL BUNDLE</span>
            <button className="btn btn-ghost" style={{ fontSize: '0.6rem' }} onClick={() => handleAction('generate_social')}>REGEN SOCIAL</button>
          </div>
          <SocialBundlePanel articleId={id} bundle={story.social_bundle || null} />

          <div className="control-block">
            <div className="block-title" style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Media Assets</span>
                <button className="btn btn-ghost" style={{ fontSize: '0.6rem' }} onClick={() => handleAction('generate_thumbnails')}>GEN THUMBNAILS</button>
            </div>
            <div style={{ aspectRatio: '16/9', background: '#000', borderRadius: '4px', marginBottom: '12px', overflow: 'hidden', border: '1px solid var(--color-border)' }}>
              {(() => {
                const imgs = typeof story.images === 'string' ? JSON.parse(story.images || '[]') : (story.images || []);
                return (imgs || []).length > 0 ? (
                  <img src={imgs[0]} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                ) : (
                  <div className="flex-center" style={{ height: '100%', color: 'var(--text-muted)' }}>NO PRIMARY IMAGE</div>
                );
              })()}
            </div>
            <button 
                className="btn btn-ghost full" 
                style={{ marginBottom: '8px' }} 
                onClick={() => handleAction('generate_audio')}
                disabled={activeActions['generate_audio']}
            >
              {activeActions['generate_audio'] ? 'GENERATING...' : 'Generate Audio News'}
            </button>
            {(() => {
              const audio = typeof story.audio === 'string' ? JSON.parse(story.audio || '{}') : (story.audio || {});
              return audio.url ? (
                <audio controls style={{ width: '100%', height: '30px', marginTop: '10px' }}>
                  <source src={`${API_BASE}${audio.url}`} type="audio/mpeg" />
                </audio>
              ) : null;
            })()}
          </div>
        </div>
      </div>
    </div>
  )
}

