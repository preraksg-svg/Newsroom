import React from 'react'

export const Loader = ({ message }) => (
  <div className="flex-center" style={{ height: '100%', flexDirection: 'column' }}>
    <div className="loader-spinner"></div>
    <div style={{ marginTop: '20px', fontSize: '0.7rem', fontWeight: 800, color: 'var(--text-muted)' }}>{message}</div>
  </div>
)

export const EmptyState = ({ title, subtitle }) => (
  <div className="flex-center" style={{ flex: 1, height: '100%', textAlign: 'center', padding: '40px' }}>
    <div>
      <div style={{ fontSize: '3.5rem', marginBottom: '24px' }}>📁</div>
      <div style={{ fontWeight: 900, color: '#fff', marginBottom: '12px', fontSize: '1.4rem' }}>{title}</div>
      <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', letterSpacing: '1.5px', textTransform: 'uppercase' }}>{subtitle}</div>
    </div>
  </div>
)

export const ErrorState = ({ error }) => (
  <div className="flex-center" style={{ flex: 1, height: '100%', textAlign: 'center', color: 'var(--c-magenta)' }}>
    <div>
      <div style={{ fontSize: '3rem' }}>⚠️</div>
      <div style={{ fontWeight: 800, marginTop: '10px' }}>SYSTEM ERROR: {error}</div>
    </div>
  </div>
)
