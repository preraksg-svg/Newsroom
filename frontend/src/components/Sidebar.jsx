import { useState, useEffect } from 'react'
import { NavLink } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { useStore } from '../store'
import { IntelligenceService } from '../services/api'

export default function Sidebar() {
  const { setStatusFilter } = useStore()
  const [timeLeft, setTimeLeft] = useState(null)
  const queryClient = useQueryClient()
  const [isOrchestrating, setIsOrchestrating] = useState(false)

  useEffect(() => {
    const fetchTime = async () => {
      try {
        const data = await IntelligenceService.getNextFetch()
        if (data && typeof data.seconds_left === 'number') {
          setTimeLeft(data.seconds_left)
        }
      } catch (err) {
        console.error('Failed to fetch next poll time', err)
      }
    }
    
    fetchTime()
    const syncInterval = setInterval(fetchTime, 30000)
    return () => clearInterval(syncInterval)
  }, [])

  useEffect(() => {
    if (timeLeft === null) return;
    
    // Auto-trigger orchestration when countdown reaches 0
    if (timeLeft <= 0) {
      if (isOrchestrating) return;
      const autoOrchestrate = async () => {
        setIsOrchestrating(true);
        try {
          await IntelligenceService.orchestrate();
          
          // Invalidate queries periodically over the next few seconds to catch the background creation
          setTimeout(() => { queryClient.invalidateQueries({ queryKey: ['news-kanban'] }) }, 1000);
          setTimeout(() => { queryClient.invalidateQueries({ queryKey: ['news-kanban'] }) }, 3000);
          setTimeout(async () => {
            queryClient.invalidateQueries({ queryKey: ['news-kanban'] });
            setIsOrchestrating(false);
            
            // Re-fetch next fetch target time to update the local timer
            try {
              const data = await IntelligenceService.getNextFetch();
              if (data && typeof data.seconds_left === 'number') {
                setTimeLeft(data.seconds_left);
              }
            } catch (syncErr) {
              console.error('Failed to sync next poll time post-orchestration', syncErr);
            }
          }, 5000);
        } catch (err) {
          console.error('Failed to auto-trigger pipeline', err);
          setIsOrchestrating(false);
        }
      };
      autoOrchestrate();
      return;
    }

    const timer = setInterval(() => {
      setTimeLeft(prev => {
        if (prev !== null && prev > 0) {
          return prev - 1;
        }
        return 0;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [timeLeft, isOrchestrating, queryClient])

  const formatTime = (totalSeconds) => {
    if (totalSeconds === null) return 'LOADING...'
    if (totalSeconds <= 0) return 'POLLING NOW...'
    const hrs = Math.floor(totalSeconds / 3600)
    const mins = Math.floor((totalSeconds % 3600) / 60)
    const secs = totalSeconds % 60
    return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  const runPipeline = async () => {
    if (window.confirm('Trigger 22-step AI Orchestration?')) {
       setIsOrchestrating(true)
       try {
         await IntelligenceService.orchestrate()
         
         // Invalidate queries periodically over the next few seconds to catch the background creation
         setTimeout(() => {
           queryClient.invalidateQueries({ queryKey: ['news-kanban'] })
         }, 1000)
         setTimeout(() => {
           queryClient.invalidateQueries({ queryKey: ['news-kanban'] })
         }, 3000)
          setTimeout(async () => {
            queryClient.invalidateQueries({ queryKey: ['news-kanban'] })
            setIsOrchestrating(false)
            
            // Re-fetch next fetch target time to update the local timer
            try {
              const data = await IntelligenceService.getNextFetch();
              if (data && typeof data.seconds_left === 'number') {
                setTimeLeft(data.seconds_left);
              }
            } catch (syncErr) {
              console.error('Failed to sync next poll time post-orchestration', syncErr);
            }
          }, 5000)
       } catch (err) {
         console.error('Failed to trigger pipeline', err)
         setIsOrchestrating(false)
       }
    }
  }

  const menuItems = [
    { label: 'News Board', icon: '📋', path: '/news' },
    { label: 'Analytics', icon: '📊', path: '/analytics' },
    { label: 'Source Learning', icon: '🧠', path: '/sources' },
    { label: 'Growth Engine', icon: '📈', path: '/growth' },
    { label: 'SEO Strategy', icon: '🌐', path: '/seo' },
    { label: 'Social Bundle', icon: '📱', path: '/social' },
    { label: 'A/B Experiments', icon: '🔬', path: '/experiments' },
    { label: 'Groq Usage', icon: '⚡', path: '/groq' },
    { label: 'Recycle Bin', icon: '♻️', path: '/recycle-bin' },
  ]

  return (
    <div className="sidebar">
      <div className="sidebar-header" style={{ padding: '24px 16px', borderBottom: '1px solid var(--color-border)' }}>
        <h1 style={{ fontSize: '1rem', fontWeight: 900, letterSpacing: '2px', color: 'var(--c-cyan)' }}>ZAPWAY</h1>
        <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)', fontWeight: 800 }}>EV INTELLIGENCE ENGINE</div>
      </div>

      <div style={{ flex: 1, padding: '16px 0', overflowY: 'auto' }}>
        <div style={{ padding: '0 16px', marginBottom: '24px' }}>
          <button onClick={runPipeline} disabled={isOrchestrating} className="btn btn-primary full" style={{ background: 'var(--c-magenta)', color: '#000', fontSize: '0.7rem', fontWeight: 800 }}>
             {isOrchestrating ? '⏳ ORCHESTRATING...' : '🚀 RUN SYSTEM PIPELINE'}
          </button>
          <div style={{ marginTop: '12px', fontSize: '0.65rem', color: 'var(--text-muted)', fontWeight: 800, textAlign: 'center', fontFamily: 'var(--font-data)', letterSpacing: '0.5px' }}>
            NEXT AUTOMATIC POLL IN: <span style={{ color: 'var(--c-cyan)', fontWeight: 900 }}>{formatTime(timeLeft)}</span>
          </div>
        </div>
        
        {menuItems.map(item => (
          <NavLink 
            key={item.label} 
            to={item.path}
            className={({ isActive }) => `sidebar-item ${isActive ? 'active' : ''}`}
            onClick={() => { if (item.path === '/news') setStatusFilter('Draft') }}
          >
            <span style={{ fontSize: '1.1rem' }}>{item.icon}</span>
            <span>{item.label}</span>
          </NavLink>
        ))}

        <div style={{ marginTop: '24px', padding: '0 16px' }}>
          <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontWeight: 800, marginBottom: '12px' }}>QUICK FILTERS</div>
          {[
            { label: 'All Signals', value: 'All', color: 'var(--text-primary)' },
            { label: 'Drafts', value: 'Draft', color: 'var(--c-yellow)' },
            { label: 'Approved', value: 'Approved', color: 'var(--c-green)' },
            { label: 'Live', value: 'Published', color: 'var(--c-cyan)' }
          ].map(f => (
            <NavLink 
              key={f.label} 
              to="/news" 
              onClick={() => setStatusFilter(f.value)} 
              className="sidebar-item" 
              style={{ fontSize: '0.75rem', padding: '8px 0', textDecoration: 'none' }}
            >
              <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: f.color, boxShadow: `0 0 10px ${f.color}44` }}></div>
              <span style={{ marginLeft: '12px' }}>{f.label}</span>
            </NavLink>
          ))}
        </div>

      </div>
    </div>
  )
}
