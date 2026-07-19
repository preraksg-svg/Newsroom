import { useState, useEffect } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query'
import { Edit2, Save, Trash2, Split, Image as ImageIcon, Music, Zap, RefreshCw, Layers, Share2, Search, X } from 'lucide-react'
import { NewsService, API_BASE } from '../services/api'
import { Loader, ErrorState } from '../components/StatusStates'

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

/* ─── PUBLISH STATUS PANEL ──────────────────────────────────────── */
function PublishStatusPanel({ articleId, story, sections }) {
  const [logs, setLogs] = useState([])
  const [lastStatus, setLastStatus] = useState('running')

  useEffect(() => {
    if (!articleId) return
    let active = true
    let interval = null

    const poll = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/publish-log/${articleId}`)
        const data = await res.json()
        if (!active) return
        setLogs(data.logs || [])
        const last = (data.logs || []).slice(-1)[0]
        if (last) setLastStatus(last.status)
        if (last && (last.status === 'success' || last.status === 'error')) {
          clearInterval(interval)
        }
      } catch {}
    }

    poll()
    interval = setInterval(poll, 1000)
    return () => { active = false; clearInterval(interval) }
  }, [articleId])

  const isDone = lastStatus === 'success'
  const isError = lastStatus === 'error'
  const isRunning = !isDone && !isError

  const stepIcons = { init: '⚡', browser: '🌐', navigate: '🔗', login: '🔑', fill: '✏️', submit: '🚀', done: '✅', error: '❌' }

  const logRows = logs.length > 0 ? logs : [
    { step: 'init', msg: 'Waiting for publish to start...', status: 'running' }
  ]

  // Compute form preview values
  const s = story || {}
  const firstSection = (sections || [])[0] || {}
  const previewFields = [
    { label: 'Headline', value: s.title || '' },
    { label: 'Meta Title', value: s.meta_title || '' },
    { label: 'Meta Desc', value: s.meta_desc || s.meta_description || '' },
    { label: 'Source', value: s.publisher || '' },
    { label: 'First Heading', value: firstSection.heading || s.title || '' },
    { label: 'Body Preview', value: (firstSection.content || '').slice(0, 80) + ((firstSection.content || '').length > 80 ? '...' : '') },
    { label: 'Author', value: 'Zapway Team' },
    { label: 'Author Initials', value: 'ZT' },
    { label: 'Designation', value: 'EV News Correspondent' },
  ]

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', fontFamily: '"JetBrains Mono", "Fira Code", monospace' }}>
      {/* Terminal log */}
      <div style={{ flex: '0 0 auto', padding: '18px 20px 12px', borderBottom: '1px solid rgba(0,240,255,0.1)' }}>
        <div style={{ fontSize: '0.65rem', color: 'rgba(0,240,255,0.5)', marginBottom: '10px', letterSpacing: '2px' }}>
          PLAYWRIGHT AUTOMATION LOG
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {logRows.map((log, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', animation: 'fadeIn 0.3s ease' }}>
              <span style={{ fontSize: '0.8rem', minWidth: '20px' }}>{stepIcons[log.step] || '•'}</span>
              <span style={{
                fontSize: '0.72rem',
                color: log.status === 'success' ? '#00ff88' : log.status === 'error' ? '#ff4444' : 'rgba(255,255,255,0.8)',
                lineHeight: 1.5
              }}>
                {log.msg}
              </span>
              {i === logRows.length - 1 && isRunning && (
                <span style={{ display: 'inline-block', width: '7px', height: '12px', background: 'var(--c-cyan)', animation: 'blink 0.8s step-end infinite', marginLeft: '2px', marginTop: '2px' }} />
              )}
            </div>
          ))}
        </div>
        {isDone && (
          <div style={{ marginTop: '12px', padding: '10px 14px', background: 'rgba(0,255,136,0.08)', border: '1px solid rgba(0,255,136,0.3)', borderRadius: '6px', fontSize: '0.72rem', color: '#00ff88', fontWeight: 700 }}>
            ✅ Article published to zapway.app successfully!
          </div>
        )}
        {isError && (
          <div style={{ marginTop: '12px', padding: '10px 14px', background: 'rgba(255,68,68,0.08)', border: '1px solid rgba(255,68,68,0.3)', borderRadius: '6px', fontSize: '0.72rem', color: '#ff6666' }}>
            ❌ Publish failed. Open Zapway manually to submit.
          </div>
        )}
      </div>

      {/* Form preview */}
      <div style={{ flex: 1, overflow: 'auto', padding: '16px 20px 20px' }}>
        <div style={{ fontSize: '0.65rem', color: 'rgba(0,240,255,0.5)', marginBottom: '12px', letterSpacing: '2px' }}>
          ARTICLE DATA BEING SUBMITTED
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {previewFields.map((f, i) => (
            <div key={i} style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '6px', padding: '10px 12px' }}>
              <div style={{ fontSize: '0.6rem', color: 'rgba(0,240,255,0.6)', letterSpacing: '1px', marginBottom: '4px' }}>{f.label.toUpperCase()}</div>
              <div style={{ fontSize: '0.75rem', color: f.value ? 'rgba(255,255,255,0.85)' : 'rgba(255,255,255,0.25)', lineHeight: 1.4 }}>
                {f.value || '—'}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default function ArticleView() {
  const { id } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const queryClient = useQueryClient()
  const [isEditMode, setIsEditMode] = useState(false)
  const [isSplitView, setIsSplitView] = useState(false)
  const [splitViewUrl, setSplitViewUrl] = useState('')
  const [isPublishing, setIsPublishing] = useState(false)
  const [splitViewTab, setSplitViewTab] = useState('source') // 'source' or 'logs'
  const [editedStory, setEditedStory] = useState(null)
  const [actionLoading, setActionLoading] = useState(null)

  const [headlineVariants, setHeadlineVariants] = useState([])
  const [thumbVariants, setThumbVariants] = useState([])
  const [showScoreBreakdown, setShowScoreBreakdown] = useState(false)
  const [showSocialModal, setShowSocialModal] = useState(false)
  const [socialBundleData, setSocialBundleData] = useState(null)

  const { data: story, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['article', id],
    queryFn: () => NewsService.getArticle(id),
    enabled: !!id
  })

  useEffect(() => {
    if (story) setEditedStory({ ...story })
  }, [story])



  const actionMutation = useMutation({
    mutationFn: ({ action, params }) => NewsService.performAction(action, id, params),
    onMutate: ({ action }) => setActionLoading(action),
    onSuccess: async (data, { action }) => {
      // If the action is queued, start polling for status
      if (data?.status === 'queued' && data?.task_id) {
        pollTaskStatus(data.task_id, action)
        return
      }

      setActionLoading(null)
      // Handle immediate results
      if (action === 'regenerate_headlines') setHeadlineVariants(data?.variants || [])
      if (action === 'generate_thumbnails' && data?.images) setThumbVariants(data.images)
      if (action === 'generate_social' && data?.social_bundle) {
        setSocialBundleData(data.social_bundle)
        setShowSocialModal(true)
      }
      if (action === 'reject_article') return navigate('/news')
      
      // FIX: Manually fetch updated state to ensure UI reflects changes instantly
      try {
        const updated = await NewsService.getArticle(id)
        setEditedStory(updated)
        queryClient.setQueryData(['article', id], updated)
      } catch (e) {
        console.error('Failed to refresh data:', e)
        refetch()
      }
    },
    onError: (err) => {
      console.error('Action failed:', err)
      setActionLoading(null)
    }
  })

  // Automatically trigger publish if navigated here with target state
  useEffect(() => {
    if (location.state?.triggerPublish && story) {
      // Clear location state immediately to avoid repeated triggers
      window.history.replaceState({}, document.title)
      
      actionMutation.mutate({ action: 'publish_article' })
      setIsPublishing(true)
      setSplitViewTab('logs')
      setSplitViewUrl('https://zapway.app/News/insert_news')
      setIsSplitView(true)
      
      // Open the original source article in a new tab (only on desktop)
      if (story?.url && window.innerWidth > 768) {
        window.open(story.url, '_blank', 'noopener,noreferrer')
      }
    }
  }, [location.state, story])

  const pollTaskStatus = async (taskId, action) => {
    let attempts = 0
    const maxAttempts = 30 // 30 seconds max
    
    const poll = async () => {
      try {
        const task = await NewsService.getTaskStatus(taskId)
        if (task.status === 'completed') {
          setActionLoading(null)
          const updated = await NewsService.getArticle(id)
          setEditedStory(updated)
          queryClient.setQueryData(['article', id], updated)
          // Specific handling for variant selection
          if (action === 'generate_thumbnails' && updated.images) {
             try { setThumbVariants(JSON.parse(updated.images)) } catch(e) {}
          }
          return
        } else if (task.status === 'failed') {
          setActionLoading(null)
          alert(`Action failed: ${task.error || 'Unknown error'}`)
          return
        }
      } catch (e) {
        console.error('Polling error:', e)
      }

      attempts++
      if (attempts < maxAttempts) {
        setTimeout(poll, 1500)
      } else {
        setActionLoading(null)
        alert('Action timed out. Check if background workers are running.')
      }
    }

    setTimeout(poll, 1500)
  }

  const publishMutation = useMutation({
    mutationFn: () => NewsService.performAction('publish_article', id),
    onSuccess: () => refetch()
  })

  const saveMutation = useMutation({
    mutationFn: () => NewsService.updateArticle(id, editedStory),
    onSuccess: () => {
      setIsEditMode(false)
      refetch()
      if (story?.status === 'Published') {
        setIsPublishing(true)
        setSplitViewTab('logs')
        setSplitViewUrl('https://zapway.app/News/insert_news')
        setIsSplitView(true)
      }
    }
  })

  const { data: rawSource } = useQuery({
    queryKey: ['raw-source', id],
    queryFn: () => NewsService.getRawSource(id),
    enabled: isSplitView
  })

  if (isLoading) return <Loader message="DECRYPTING ARTICLE INTELLIGENCE..." />
  if (isError) {
    if (error.message.includes('Article not found') || error.message.includes('404')) {
      return (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '60vh', padding: '24px', textAlign: 'center' }}>
          <div style={{ fontSize: '3rem', marginBottom: '16px' }}>🔍</div>
          <h2 style={{ fontFamily: 'var(--font-headline)', color: 'var(--c-magenta)', marginBottom: '16px' }}>ARTICLE NOT FOUND</h2>
          <p style={{ color: 'var(--text-secondary)', maxWidth: '480px', marginBottom: '32px', fontSize: '0.95rem', lineHeight: '1.6' }}>
            This news signal is not available in the active database. The database may have been reset due to a system deployment. Please return to the dashboard.
          </p>
          <button className="btn btn-primary" onClick={() => navigate('/news')}>
            RETURN TO DASHBOARD
          </button>
        </div>
      )
    }
    return <ErrorState error={error.message} />
  }
  if (!story || !editedStory) return null

  // Helper to safely parse JSON or return as is
  const safeParse = (data, fallback = []) => {
    if (!data) return fallback
    let parsed = data
    if (typeof data !== 'object') {
      try {
        parsed = JSON.parse(data)
      } catch (e) {
        return fallback
      }
    }
    
    if (Array.isArray(fallback) && !Array.isArray(parsed)) {
       return fallback
    }
    return parsed
  }

  const sections = safeParse(editedStory.sections, [])
  const aiSummary = safeParse(editedStory.ai_summary, {})
  const images = safeParse(editedStory.images, [])
  const audio = safeParse(editedStory.audio, {})


  const handleInputChange = (field, value) => {
    setEditedStory(prev => ({ ...prev, [field]: value }))
  }

  const handleSectionChange = (index, field, value) => {
    const newSections = [...sections]
    newSections[index][field] = value
    setEditedStory(prev => ({ ...prev, sections: JSON.stringify(newSections) }))
  }

  const normalizeUrl = (url) => {
    if (!url) return ''
    let actualUrl = url
    if (typeof url === 'object') {
      actualUrl = url.url || url.src || ''
    }
    if (!actualUrl || typeof actualUrl !== 'string') return ''
    if (actualUrl.startsWith('http://')) {
      return actualUrl.replace('http://', 'https://')
    }
    if (actualUrl.startsWith('https://') || actualUrl.startsWith('data:')) return actualUrl
    return `${API_BASE}${actualUrl}`
  }
  const renderFormattedContent = (text) => {
    if (!text) return null
    const lines = text.split('\n')
    const blocks = []
    let currentList = null

    lines.forEach((line) => {
      const trimmed = line.trim()
      const bulletMatch = trimmed.match(/^([\*\-\u2022•]|\d+\.)\s+(.*)$/)
      
      if (bulletMatch) {
        if (!currentList) {
          currentList = []
        }
        currentList.push(bulletMatch[2])
      } else {
        if (currentList) {
          blocks.push({ type: 'list', items: currentList })
          currentList = null
        }
        if (trimmed) {
          blocks.push({ type: 'p', text: line })
        }
      }
    });

    if (currentList) {
      blocks.push({ type: 'list', items: currentList })
    }

    return blocks.map((block, idx) => {
      if (block.type === 'list') {
        return (
          <ul key={idx} style={{ margin: '8px 0 8px 24px', paddingLeft: '0', listStyleType: 'disc' }}>
            {block.items.map((item, liIdx) => (
              <li key={liIdx} style={{ color: 'var(--text-secondary)', marginBottom: '4px' }}>{item}</li>
            ))}
          </ul>
        )
      }
      
      // Check for inline markdown image ![alt](url)
      const imgMatch = block.text.match(/!\[(.*?)\]\((.*?)\)/)
      if (imgMatch) {
        return (
          <div key={idx} style={{ margin: '20px 0', textAlign: 'center' }}>
            <img 
              src={normalizeUrl(imgMatch[2])} 
              alt={imgMatch[1]} 
              style={{ maxWidth: '100%', maxHeight: '450px', borderRadius: '8px', border: '1px solid var(--color-border)', boxShadow: 'var(--glow-cyan)' }} 
            />
            {imgMatch[1] && <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '8px' }}>{imgMatch[1]}</div>}
          </div>
        )
      }

      return <p key={idx} style={{ margin: '0 0 12px 0', whiteSpace: 'pre-wrap' }}>{block.text}</p>
    })
  }

  return (
    <div className="intelligence-terminal">
      <div className="terminal-header">
        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
          <button className="btn btn-ghost" onClick={() => navigate('/news')}>&lt;- GO TO KANBAN</button>
          <div className={`edit-toggle ${isEditMode ? 'active' : ''}`} onClick={() => setIsEditMode(!isEditMode)}>
            {isEditMode ? <Save size={14} /> : <Edit2 size={14} />}
            <span style={{ marginLeft: '8px' }}>{isEditMode ? 'SAVE MODE' : 'EDIT MODE'}</span>
          </div>
          <span className={`badge ${
            story.status === 'Draft' ? 'badge-draft' : 
            story.status === 'Approved' ? 'badge-approved' : 'badge-published'
          }`}>
            {story.status?.toUpperCase() || 'UNKNOWN'}
          </span>
          <div className={`edit-toggle ${isSplitView ? 'active' : ''}`} onClick={() => {
            const nextVal = !isSplitView
            setIsSplitView(nextVal)
            if (nextVal) {
              setSplitViewTab('source')
              setSplitViewUrl(story?.url || '')
            }
          }}>
             <Split size={14} />
             <span style={{ marginLeft: '8px' }}>SPLIT VIEW</span>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          {story.status === 'Draft' && (
            <button 
              className="btn btn-primary" 
              style={{ background: 'var(--c-green)', color: '#000' }} 
              onClick={() => actionMutation.mutate({ action: 'approve_article' })}
              disabled={actionLoading === 'approve_article'}
            >
              {actionLoading === 'approve_article' ? 'APPROVING...' : 'APPROVE SIGNAL'}
            </button>
          )}
          {story.status !== 'Published' && (
            <button 
              className="btn btn-primary" 
              style={{ background: 'var(--c-cyan)', color: '#000', position: 'relative' }} 
              onClick={() => {
                actionMutation.mutate({ action: 'publish_article' })
                setIsPublishing(true)
                setSplitViewTab('logs')
                setSplitViewUrl('https://zapway.app/News/insert_news')
                setIsSplitView(true)
                if (story?.url && window.innerWidth > 768) {
                  window.open(story.url, '_blank', 'noopener,noreferrer')
                }
              }}
              disabled={actionLoading === 'publish_article'}
            >
              {actionLoading === 'publish_article' ? '⚡ PUBLISHING...' : '🚀 PUBLISH TO ZAPWAY'}
            </button>
          )}
          {story.status === 'Published' && (
            <button 
              className="btn btn-ghost" 
              style={{ color: 'var(--c-magenta)', border: '1px solid var(--c-magenta)' }}
              onClick={() => {
                if (confirm('Move this article back to Drafts?')) {
                  actionMutation.mutate({ action: 'revert_to_draft' })
                }
              }}
              disabled={actionLoading === 'revert_to_draft'}
            >
              {actionLoading === 'revert_to_draft' ? 'REVERTING...' : 'REVERT TO DRAFT'}
            </button>
          )}
          {isEditMode && (
            <button className="btn btn-primary" onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>
              {saveMutation.isPending ? 'SAVING...' : 'SAVE CHANGES'}
            </button>
          )}
        </div>
      </div>

      <div className="terminal-body">
        <div className="terminal-content">
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
                  value={editedStory.meta_title || ''}
                  onChange={(e) => handleInputChange('meta_title', e.target.value)}
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
                  value={editedStory.meta_desc || ''}
                  onChange={(e) => handleInputChange('meta_desc', e.target.value)}
                />
              ) : (
                <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{story.meta_desc || story.meta_description || 'Not generated'}</span>
              )}
            </div>
          </div>

          {isEditMode ? (
            <input 
              className="card-title" 
              style={{ fontSize: '2.5rem', width: '100%', background: 'transparent', border: '1px dashed var(--color-border)', color: '#fff', marginBottom: '24px', outline: 'none' }}
              value={editedStory.title}
              onChange={(e) => handleInputChange('title', e.target.value)}
            />
          ) : (
            <h1 style={{ fontSize: '2.5rem', fontWeight: 900, marginBottom: '24px' }}>{story.title}</h1>
          )}

          {/* HEADLINE VARIANTS SELECTOR */}
          {headlineVariants.length > 0 && (
            <div className="control-block animate-slide-in" style={{ border: '1px solid var(--c-cyan)', marginBottom: '24px' }}>
               <div className="block-title" style={{ color: 'var(--c-cyan)' }}>SELECT VIRAL VARIANT</div>
               <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                 {headlineVariants.map((v, i) => (
                   <div key={i} className="variant-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px', background: 'rgba(255,255,255,0.05)', borderRadius: '4px' }}>
                     <div style={{ flex: 1, marginRight: '16px' }}>
                       <div style={{ fontSize: '1rem', fontWeight: 600, color: '#fff' }}>{v.headline}</div>
                       <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                         PATTERN: <span style={{ color: 'var(--c-cyan)' }}>{v.pattern_type?.toUpperCase()}</span> | 
                         SCORE: <span style={{ color: (v.score_estimate || 0) > 70 ? 'var(--c-green)' : 'var(--text-muted)' }}>{v.score_estimate}%</span>
                       </div>
                     </div>
                     <button className="btn btn-ghost" style={{ padding: '4px 12px', fontSize: '0.75rem' }} onClick={() => actionMutation.mutate({ action: 'select_headline', params: { headline: v.headline } })}>SELECT</button>
                   </div>
                 ))}
               </div>
            </div>
          )}


          {/* DYNAMIC SECTIONS */}
          {sections.length > 0 ? (
            sections.map((s, i) => {
              const rawContent = s.content || s.body || '';
              let textValue = '';
              if (Array.isArray(rawContent)) {
                textValue = rawContent.map(item => typeof item === 'object' ? (item.fact || '') : item).join('\n');
              } else {
                textValue = String(rawContent);
              }

              return (
                <div key={i} style={{ marginBottom: '32px' }}>
                  {isEditMode ? (
                    <>
                      <input 
                        style={{ fontSize: '1.2rem', fontWeight: 700, width: '100%', background: 'transparent', border: 'none', borderBottom: '1px solid var(--color-border)', color: 'var(--c-cyan)', marginBottom: '8px', outline: 'none' }}
                        value={s.heading || s.title || ''}
                        onChange={(e) => handleSectionChange(i, 'heading', e.target.value)}
                      />
                      <textarea 
                        style={{ width: '100%', minHeight: '150px', background: 'transparent', border: 'none', color: 'var(--text-secondary)', fontSize: '1rem', outline: 'none', resize: 'vertical' }}
                        value={textValue}
                        onChange={(e) => handleSectionChange(i, 'content', e.target.value)}
                      />
                    </>
                  ) : (
                    <>
                      {(s.heading || s.title) && <h3 style={{ marginBottom: '12px', color: 'var(--text-primary)' }}>{s.heading || s.title}</h3>}
                      {Array.isArray(rawContent) ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                          {rawContent.map((item, idx) => {
                            if (typeof item === 'object') {
                              return (
                                <p key={idx} style={{ color: 'var(--text-secondary)', fontSize: '1.05rem', lineHeight: '1.6', margin: '0 0 8px 0' }}>
                                  {item.fact}
                                  {item.provenance_url && (
                                    <a 
                                      href={item.provenance_url} 
                                      target="_blank" 
                                      rel="noreferrer" 
                                      style={{ marginLeft: '8px', fontSize: '0.75rem', color: 'var(--c-cyan)', textDecoration: 'underline' }}
                                    >
                                      [source]
                                    </a>
                                  )}
                                </p>
                              );
                            }
                            return <p key={idx} style={{ color: 'var(--text-secondary)', fontSize: '1.05rem', lineHeight: '1.6', margin: '0 0 8px 0' }}>{item}</p>;
                          })}
                        </div>
                      ) : (
                        <div style={{ color: 'var(--text-secondary)', fontSize: '1.05rem', lineHeight: '1.6' }}>
                          {renderFormattedContent(textValue)}
                        </div>
                      )}
                    </>
                  )}
                </div>
              );
            })
          ) : (
            /* Fallback: show original_content when no sections generated yet */
            <div style={{ marginBottom: '32px' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '12px', padding: '8px 12px', background: 'rgba(255,165,0,0.08)', border: '1px solid rgba(255,165,0,0.2)', borderRadius: '4px' }}>
                [!] SECTIONS NOT YET GENERATED - RE-SUMMARIZE TO STRUCTURE ARTICLE
              </div>
              {editedStory.original_content ? (
                <p style={{ color: 'var(--text-secondary)', fontSize: '1.05rem', lineHeight: '1.8', whiteSpace: 'pre-wrap' }}>
                  {editedStory.original_content.slice(0, 2000)}{editedStory.original_content.length > 2000 ? '...' : ''}
                </p>
              ) : (
                <p style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>No content available.</p>
              )}
            </div>
          )}

          {/* THUMBNAIL VARIANTS SELECTOR */}
          {thumbVariants.length > 0 && (
            <div className="control-block animate-slide-in" style={{ border: '1px solid var(--c-green)', marginBottom: '24px' }}>
               <div className="block-title" style={{ color: 'var(--c-green)' }}>SELECT THUMBNAIL VARIANT</div>
               <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
                 {thumbVariants.map((img, i) => (
                   <div key={i} style={{ cursor: 'pointer', position: 'relative' }} onClick={() => actionMutation.mutate({ action: 'select_thumbnail', params: { image_url: img } })}>
                     <img src={normalizeUrl(img)} style={{ width: '100%', borderRadius: '4px' }} />
                     <div style={{ position: 'absolute', bottom: '0', left: '0', right: '0', background: 'rgba(0,0,0,0.5)', fontSize: '0.6rem', padding: '4px', textAlign: 'center' }}>CHOOSE</div>
                   </div>
                 ))}
               </div>
            </div>
          )}

          {/* AUDIO SECTION — Images are now displayed inline within article content */}
          {audio.url && (
            <div style={{ marginTop: '40px', borderTop: '1px solid var(--color-border)', paddingTop: '24px' }}>
              <div className="control-block" style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
                <Music className="text-cyan" />
                <audio controls src={normalizeUrl(audio.url)} style={{ flex: 1, height: '32px' }} />
              </div>
            </div>
          )}
        </div>

        {isSplitView && (
          <div className="terminal-content split-view-panel" style={{ background: '#080c10', display: 'flex', flexDirection: 'column', padding: 0 }}>
            {/* Header bar */}
            <div style={{ margin: '0', padding: '12px 16px', background: 'rgba(0,240,255,0.06)', borderBottom: '1px solid rgba(0,240,255,0.3)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', background: 'var(--c-cyan)', boxShadow: '0 0 8px var(--c-cyan)', animation: 'pulse 1.2s infinite' }} />
                
                {/* Tab Toggles */}
                <div style={{ display: 'flex', gap: '4px', background: 'rgba(255,255,255,0.05)', padding: '2px', borderRadius: '4px' }}>
                  <button 
                    onClick={() => setSplitViewTab('source')}
                    style={{ fontSize: '0.65rem', padding: '4px 8px', border: 'none', borderRadius: '3px', cursor: 'pointer', background: splitViewTab === 'source' ? 'var(--c-cyan)' : 'transparent', color: splitViewTab === 'source' ? '#000' : 'var(--text-muted)', fontWeight: 700 }}
                  >
                    📰 ORIGINAL SOURCE
                  </button>
                  <button 
                    onClick={() => setSplitViewTab('logs')}
                    style={{ fontSize: '0.65rem', padding: '4px 8px', border: 'none', borderRadius: '3px', cursor: 'pointer', background: splitViewTab === 'logs' ? 'var(--c-cyan)' : 'transparent', color: splitViewTab === 'logs' ? '#000' : 'var(--text-muted)', fontWeight: 700 }}
                  >
                    ⚡ PUBLISH LOGS
                  </button>
                </div>
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <a
                  href="https://zapway.app/News/insert_news"
                  target="_blank"
                  rel="noreferrer"
                  style={{ fontSize: '0.7rem', padding: '4px 10px', color: 'var(--c-cyan)', background: 'transparent', border: '1px solid var(--c-cyan)', borderRadius: '4px', textDecoration: 'none', fontWeight: 700 }}
                >
                  OPEN ZAPWAY ↗
                </a>
                <button
                  onClick={() => { setIsSplitView(false); setSplitViewUrl('') }}
                  style={{ fontSize: '0.7rem', padding: '4px 10px', color: 'var(--text-muted)', background: 'transparent', border: '1px solid var(--color-border)', borderRadius: '4px', cursor: 'pointer', fontWeight: 700 }}
                >
                  ✕ CLOSE
                </button>
              </div>
            </div>

            {/* Split View Content */}
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              {splitViewTab === 'logs' ? (
                <PublishStatusPanel articleId={id} story={story} sections={sections} />
              ) : (
                story?.url ? (
                  <iframe 
                    src={`${API_BASE}/api/proxy?url=${encodeURIComponent(story.url)}`} 
                    title="Original Source" 
                    sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox"
                    style={{ width: '100%', height: '100%', border: 'none', background: '#fff' }} 
                  />
                ) : (
                  <div style={{ padding: '40px', color: 'var(--text-muted)', textAlign: 'center', fontFamily: 'monospace', fontSize: '0.8rem' }}>
                    No source URL available for this article.
                  </div>
                )
              )}
            </div>
          </div>
        )}


        <div className="terminal-sidebar">
           <div className="control-block">
             <div className="block-title">EDITORIAL SCORE</div>
             <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
               <div style={{ fontSize: '3.5rem', fontWeight: 900, color: true ? 'var(--c-green)' : 'var(--c-cyan)' }}>
                 {(story.final_score || 0).toFixed(0)}
               </div>
               <div style={{ color: 'var(--text-muted)', fontWeight: 700 }}>/ 100</div>
             </div>
             <div className="score-meter" style={{ height: '8px', marginTop: '10px' }}>
               <div className="score-fill" style={{ width: `${story.final_score || 0}%`, background: true ? 'var(--c-green)' : 'var(--c-cyan)' }} />
             </div>
             <button className="btn btn-ghost full" style={{ marginTop: '12px', fontSize: '0.7rem' }} onClick={() => setShowScoreBreakdown(!showScoreBreakdown)}>
               {showScoreBreakdown ? 'HIDE BREAKDOWN' : 'VIEW BREAKDOWN'}
             </button>
             {showScoreBreakdown && (
               <div className="animate-slide-in" style={{ marginTop: '16px', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                 <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}><span>Credibility:</span> <span>{story.score_credibility || 0}</span></div>
                 <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}><span>Intelligence:</span> <span>{story.score_intelligence || 0}</span></div>
                 <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}><span>Virality:</span> <span>{story.score_virality || 0}</span></div>
                 <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}><span>Timeliness:</span> <span>{story.score_time || 0}</span></div>
                 <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}><span>Relevance:</span> <span>{story.score_relevance || 0}</span></div>
               </div>
             )}
           </div>

           <div className="control-block">
             <div className="block-title">INTELLIGENCE ACTIONS</div>
             <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
               <button className="btn full" onClick={() => actionMutation.mutate({ action: 'calculate_score' })} disabled={actionLoading === 'calculate_score'}>
                 <RefreshCw size={14} className={actionLoading === 'calculate_score' ? 'animate-spin' : ''} /> RE-CALCULATE SCORE
               </button>
               <button className="btn full" onClick={() => actionMutation.mutate({ action: 'generate_summary' })} disabled={actionLoading === 'generate_summary'}>
                 {actionLoading === 'generate_summary' ? <RefreshCw className="animate-spin" /> : <Layers size={16} />}
                 RE-SUMMARIZE
               </button>
               <button className="btn full" onClick={() => actionMutation.mutate({ action: 'regenerate_headlines' })} disabled={actionLoading === 'regenerate_headlines'}>
                 {actionLoading === 'regenerate_headlines' ? <RefreshCw className="animate-spin" /> : <Zap size={16} />}
                 REGEN HEADLINES
               </button>
               <button className="btn full" onClick={() => actionMutation.mutate({ action: 'generate_thumbnails' })} disabled={actionLoading === 'generate_thumbnails'}>
                 {actionLoading === 'generate_thumbnails' ? <RefreshCw className="animate-spin" /> : <ImageIcon size={16} />}
                 GEN THUMBNAILS
               </button>
               <button className="btn full" onClick={() => actionMutation.mutate({ action: 'generate_audio' })} disabled={actionLoading === 'generate_audio'}>
                 {actionLoading === 'generate_audio' ? <RefreshCw className="animate-spin" /> : <Music size={16} />}
                 GEN AUDIO
               </button>
               <button className="btn full" onClick={() => actionMutation.mutate({ action: 'generate_social' })} disabled={actionLoading === 'generate_social'}>
                 {actionLoading === 'generate_social' ? <RefreshCw className="animate-spin" /> : <Share2 size={16} />}
                 GEN SOCIAL
               </button>
               <button className="btn full" style={{ borderColor: 'var(--c-magenta)', color: 'var(--c-magenta)' }} onClick={() => actionMutation.mutate({ action: 'reject_article' })} disabled={actionLoading === 'reject_article'}>
                 <Trash2 size={16} /> REJECT
               </button>
             </div>
           </div>

           <div className="control-block">
             <div className="block-title">SIGNAL DATA</div>
             <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
               <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                 <span>SOURCE:</span>
                 <span style={{ color: 'var(--c-cyan)' }}>{story.publisher}</span>
               </div>
               <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                 <span>INGESTED:</span>
                  <span>{(() => {
                    if (!story.created_at) return ''
                    let parseStr = String(story.created_at).replace(' ', 'T')
                    if (!parseStr.includes('Z') && !parseStr.includes('+') && !parseStr.includes('-')) {
                      parseStr += 'Z'
                    }
                    return new Date(parseStr).toLocaleString()
                  })()}</span>
               </div>
               <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                 <span>STATUS:</span>
                 <span style={{ color: 'var(--c-green)' }}>{story.status}</span>
               </div>
             </div>
            </div>
         </div>
      </div>
      <SocialModal 
        isOpen={showSocialModal} 
        onClose={() => setShowSocialModal(false)} 
        bundle={socialBundleData} 
      />
    </div>
  )
}
