const isDev = window.location.port === '5173' || window.location.port === '5174'
export const API_BASE = isDev ? 'http://localhost:8000' : ''

const fetchApi = async (path, options = {}) => {
  try {
    const res = await fetch(`${API_BASE}${path}`, options)
    const json = await res.json()
    if (!json.success) throw new Error(json.error || 'API Error')
    return json.data
  } catch (err) {
    console.error(`[API Error] ${path}:`, err)
    throw err
  }
}

export const NewsService = {
  getNews: (params) => {
    const q = new URLSearchParams(params).toString()
    return fetchApi(`/api/news?${q}`)
  },
  getArticle: (id) => fetchApi(`/api/news/${id}`),
  getRawSource: (id) => fetchApi(`/api/raw-source/${id}`),
  updateArticle: (id, data) => fetchApi(`/api/news/update?record_id=${id}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  }),
  getRejected: () => fetchApi('/api/rejected'),
  restoreArticle: (id) => fetchApi(`/api/restore/${id}`, { method: 'POST' }),
  performAction: (action, articleId, params = {}) => fetchApi('/api/action', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action, article_id: articleId, params })
  }),
  getTaskStatus: (taskId) => fetchApi(`/api/tasks/${taskId}`)
}

export const AnalyticsService = {
  getStats: () => fetchApi('/api/analytics'),
  getGroq: () => fetchApi('/api/groq-usage'),
  getGrowth: () => fetchApi('/api/growth'),
  getSEO: () => fetchApi('/api/seo'),
  getExperiments: () => fetchApi('/api/experiments')
}

export const IntelligenceService = {
  getSources: () => fetchApi('/api/sources'),
  getSocial: (id) => fetchApi(`/api/social/${id}`),
  orchestrate: () => fetchApi('/api/orchestrate', { method: 'POST' }),
  getNextFetch: () => fetchApi('/api/next-fetch')
}
