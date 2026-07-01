import { useQuery } from '@tanstack/react-query'
import { AreaChart, Area, XAxis, Tooltip, ResponsiveContainer, YAxis } from 'recharts'
import { useStore } from '../store'
import { useEffect } from 'react'

const dummyEngagementData = [
  { name: 'Mon', views: 4000, interactions: 2400 },
  { name: 'Tue', views: 3000, interactions: 1398 },
  { name: 'Wed', views: 2000, interactions: 9800 },
  { name: 'Thu', views: 2780, interactions: 3908 },
  { name: 'Fri', views: 1890, interactions: 4800 },
  { name: 'Sat', views: 2390, interactions: 3800 },
  { name: 'Sun', views: 3490, interactions: 4300 },
]

export default function GroqUsagePanel() {
  const setLlmDisabled = useStore(state => state.setLlmDisabled)

  const { data, isLoading } = useQuery({
    queryKey: ['groq-usage'],
    queryFn: async () => {
      const res = await fetch('/api/groq-usage')
      if (!res.ok) throw new Error('Network error')
      return res.json()
    },
    refetchInterval: 30000 // Poll every 30s
  })

  useEffect(() => {
    if (data?.usage_percentage > 90) {
      setLlmDisabled(true)
    } else {
      setLlmDisabled(false)
    }
  }, [data?.usage_percentage, setLlmDisabled])

  return (
    <div className="matrix-col" style={{ flex: '0 0 350px' }}>
      
      {/* Groq Intelligence Limit Monitor */}
      <div style={{ padding: '20px', borderBottom: '1px solid var(--color-glass-border)' }}>
        <h3 style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '15px' }}>GROQ TOKEN LIMITS</h3>
        {isLoading ? (
          <span style={{ color: 'var(--c-cyan)', fontSize: '0.8rem' }}>FETCHING FROM NODE...</span>
        ) : (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <span style={{ color: data?.usage_percentage > 80 ? 'var(--c-red)' : 'var(--c-green)' }}>
                {data?.total_tokens.toLocaleString()} / {data?.limit.toLocaleString()}
              </span>
              <span style={{ fontWeight: 'bold' }}>{data?.usage_percentage.toFixed(1)}%</span>
            </div>
            <div style={{ height: '8px', background: 'var(--color-bg)', borderRadius: '4px', overflow: 'hidden' }}>
              <div 
                style={{ 
                  height: '100%', 
                  width: `${data?.usage_percentage}%`, 
                  background: data?.usage_percentage > 90 ? 'var(--c-red)' : data?.usage_percentage > 80 ? 'var(--c-magenta)' : 'var(--c-green)',
                  transition: 'width 0.5s ease-out'
                }} 
              />
            </div>
            {data?.usage_percentage > 90 && (
              <div style={{ marginTop: '10px', fontSize: '0.75rem', color: 'var(--c-red)', border: '1px solid var(--c-red)', padding: '5px', borderRadius: '4px', background: 'rgba(255,0,0,0.1)' }}>
                ⚠ SYSTEM LOCK: API generation halted to prevent token exhaustion.
              </div>
            )}
          </div>
        )}
      </div>

      {/* Recharts Analytics Rendering */}
      <div style={{ padding: '20px', flex: 1, display: 'flex', flexDirection: 'column' }}>
        <h3 style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '15px' }}>ENGAGEMENT VELOCITY</h3>
        <div style={{ flex: 1, minHeight: '150px' }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={dummyEngagementData} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="colorViews" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--c-cyan)" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="var(--c-cyan)" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <XAxis dataKey="name" stroke="var(--text-muted)" fontSize={10} tickLine={false} axisLine={false} />
              <YAxis stroke="var(--text-muted)" fontSize={10} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={{ background: 'var(--color-panel)', border: '1px solid var(--c-cyan)', borderRadius: '8px' }} />
              <Area type="monotone" dataKey="views" stroke="var(--c-cyan)" fillOpacity={1} fill="url(#colorViews)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
      
    </div>
  )
}
