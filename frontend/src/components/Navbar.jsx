import { memo, useState, useEffect } from 'react'

const Navbar = memo(() => {
  const [time, setTime] = useState(new Date())

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  return (
    <header style={{ 
      height: '50px', 
      borderBottom: '1px solid var(--color-border)', 
      display: 'flex', 
      alignItems: 'center', 
      justifyContent: 'space-between', 
      padding: '0 20px',
      background: 'var(--color-bg)',
      flexShrink: 0
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{ width: '12px', height: '12px', background: 'var(--c-cyan)', borderRadius: '50%' }}></div>
          <span style={{ fontWeight: 900, letterSpacing: '2px', fontSize: '1rem' }}>ZAPWAY</span>
        </div>
        <div style={{ display: 'flex', gap: '15px', color: 'var(--text-muted)', fontSize: '0.7rem', fontWeight: 800 }}>
          <span>LATENCY: 14MS</span>
          <span>UPTIME: 99.9%</span>
          <span>NET: SECURE_WS</span>
        </div>
      </div>
      
      <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
            <span style={{ fontSize: '0.6rem', color: 'var(--text-muted)', fontWeight: 800 }}>OPTIMIZATION LEVEL</span>
            <span style={{ fontSize: '0.75rem', color: 'var(--c-magenta)', fontWeight: 900 }}>MAXIMUM</span>
          </div>
          <div style={{ width: '40px', height: '4px', background: 'rgba(255,0,85,0.1)', borderRadius: '2px' }}>
            <div style={{ width: '85%', height: '100%', background: 'var(--c-magenta)', borderRadius: '2px' }}></div>
          </div>
        </div>

        <div style={{ fontVariantNumeric: 'tabular-nums', fontWeight: 800, fontSize: '0.9rem', color: 'var(--text-primary)' }}>
          {time.toLocaleTimeString('en-IN', { hour12: false })} <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>IST</span>
        </div>
      </div>
    </header>
  )
})

export default Navbar
