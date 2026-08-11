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
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
        <div style={{ fontVariantNumeric: 'tabular-nums', fontWeight: 800, fontSize: '0.9rem', color: 'var(--text-primary)' }}>
          {time.toLocaleTimeString('en-IN', { hour12: false })} <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>IST</span>
        </div>
      </div>
    </header>
  )
})

export default Navbar
