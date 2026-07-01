import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import Navbar from './components/Navbar'
import Sidebar from './components/Sidebar'

// Pages
import NewsBoard from './pages/NewsBoard'
import ArticleView from './pages/ArticleView'
import { 
  SourceLearningView, AnalyticsView, GroqUsageView,
  GrowthEngineView, SEOMatrixView, SocialBundleView, ExperimentsView
} from './pages/IntelligencePages'

export default function App() {
  return (
    <div className="terminal-layout">
      <Navbar />
      <div className="data-matrix">
        <Sidebar />
        <main className="content-area">
          <Routes>
            <Route path="/" element={<Navigate to="/news" />} />
            <Route path="/news" element={<NewsBoard />} />
            <Route path="/article/:id" element={<ArticleView />} />
            <Route path="/sources" element={<SourceLearningView />} />
            <Route path="/analytics" element={<AnalyticsView />} />
            <Route path="/groq" element={<GroqUsageView />} />
            <Route path="/growth" element={<GrowthEngineView />} />
            <Route path="/seo" element={<SEOMatrixView />} />
            <Route path="/social" element={<SocialBundleView />} />
            <Route path="/experiments" element={<ExperimentsView />} />
            <Route path="/recycle-bin" element={<NewsBoard isRecycleBin={true} />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}
