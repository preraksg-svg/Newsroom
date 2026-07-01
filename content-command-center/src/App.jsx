import React, { useState, useEffect } from 'react';
import { 
  Sparkles, Calendar as CalendarIcon, BookOpen, Settings, 
  Plus, X, Copy, Check, Video, FileText, Upload, RefreshCw, AlertCircle, Trash2, ChevronLeft, ChevronRight, File
} from 'lucide-react';

const AI_SERVICES = [
  { id: 'claude', name: 'Claude.ai', url: 'https://claude.ai/chats', partition: 'persist:claude' },
  { id: 'notebooklm', name: 'NotebookLM', url: 'https://notebooklm.google.com/', partition: 'persist:notebooklm' },
  { id: 'gemini', name: 'Gemini', url: 'https://gemini.google.com/', partition: 'persist:gemini' },
  { id: 'sarvam', name: 'Sarvam AI', url: 'https://www.sarvam.ai/', partition: 'persist:sarvam' }
];

export default function App() {
  const [activeTab, setActiveTab] = useState('workspace'); // workspace | calendar | library | settings
  const [ideas, setIdeas] = useState([]);
  const [calendar, setCalendar] = useState([]);
  const [settings, setSettings] = useState({ youtubeOauth: {}, publishDefaults: {} });
  const [daemonEnabled, setDaemonEnabled] = useState(false);

  // Zone A: AI Tab Dock State
  const [openAiTabs, setOpenAiTabs] = useState([
    { id: 'notebooklm', name: 'NotebookLM', url: 'https://notebooklm.google.com/', partition: 'persist:notebooklm' },
    { id: 'gemini', name: 'Gemini', url: 'https://gemini.google.com/', partition: 'persist:gemini' }
  ]);
  const [activeAiTabId, setActiveAiTabId] = useState('notebooklm');

  // Zone B: Calendar State (Month Navigation)
  const [currentDate, setCurrentDate] = useState(new Date());
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [newCalendarEntry, setNewCalendarEntry] = useState({
    title: '',
    note: '',
    filePath: '',
    platform: 'YouTube', // YouTube | Reddit | Instagram | X
    status: 'Scheduled' // Scheduled | Posted
  });

  // Zone C: Publish Console Form
  const [publishPlatform, setPublishPlatform] = useState('youtube');
  const [publishForm, setPublishForm] = useState({
    title: '',
    description: '',
    tags: '',
    hashtags: '',
    videoPath: '',
    privacyStatus: 'private'
  });
  const [oauthCode, setOauthCode] = useState('');
  const [authUrl, setAuthUrl] = useState('');
  const [uploadStatus, setUploadStatus] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    if (window.api) {
      const dbIdeas = await window.api.getIdeas();
      const dbCalendar = await window.api.getCalendar();
      const dbSettings = await window.api.getSettings();
      const daemon = await window.api.checkDaemonStatus();

      setIdeas(dbIdeas);
      setCalendar(dbCalendar);
      setSettings(dbSettings || { youtubeOauth: {}, publishDefaults: {} });
      setDaemonEnabled(daemon.enabled);
    }
  };

  // Open an AI webview tab
  const openAiService = (service) => {
    if (!openAiTabs.some(t => t.id === service.id)) {
      setOpenAiTabs([...openAiTabs, service]);
    }
    setActiveAiTabId(service.id);
  };

  // Close AI webview tab
  const closeAiTab = (id) => {
    const remaining = openAiTabs.filter(t => t.id !== id);
    setOpenAiTabs(remaining);
    if (activeAiTabId === id && remaining.length > 0) {
      setActiveAiTabId(remaining[0].id);
    }
  };

  // Save calendar entry
  const handleSaveCalendarEntry = async (e) => {
    e.preventDefault();
    if (!newCalendarEntry.title.trim()) return;
    
    if (window.api) {
      const saved = await window.api.saveCalendarEntry({
        ...newCalendarEntry,
        date: selectedDate
      });
      
      // Auto-populate to ideas catalog (Zone D: Content Library)
      await window.api.saveIdea({
        title: newCalendarEntry.title,
        content: newCalendarEntry.note,
        type: newCalendarEntry.platform.toLowerCase(),
        tags: newCalendarEntry.platform
      });

      setNewCalendarEntry({
        title: '',
        note: '',
        filePath: '',
        platform: 'YouTube',
        status: 'Scheduled'
      });
      loadData();
    }
  };

  // Toggle status (Scheduled <=> Posted)
  const togglePostedStatus = async (item) => {
    if (window.api) {
      await window.api.saveCalendarEntry({
        ...item,
        status: item.status === 'Posted' ? 'Scheduled' : 'Posted'
      });
      loadData();
    }
  };

  // Delete calendar item
  const handleDeleteCalendarItem = async (id) => {
    if (window.api) {
      await window.api.deleteCalendarEntry(id);
      loadData();
    }
  };

  // Populate publish form from library item
  const handleLoadToPublish = (item) => {
    setPublishForm({
      title: item.title,
      description: item.note || item.content || '',
      tags: item.platform === 'YouTube' ? 'tutorial, ev, news' : '',
      hashtags: item.platform === 'YouTube' ? '#tutorial' : '',
      videoPath: item.filePath || '',
      privacyStatus: 'private'
    });
    setPublishPlatform(item.platform ? item.platform.toLowerCase() : 'youtube');
    setActiveTab('workspace');
  };

  // YouTube OAuth
  const handleGetAuthUrl = async () => {
    if (!window.api) return;
    setUploadStatus('Retrieving Google authentication page URL...');
    const res = await window.api.youtubeAuthUrl();
    if (res.success) {
      setAuthUrl(res.url);
      setUploadStatus('Click the link below, authorize the app, then paste the code here.');
    } else {
      setUploadStatus(`Error: ${res.error}`);
    }
  };

  const handleVerifyCode = async () => {
    if (!window.api || !oauthCode) return;
    setUploadStatus('Verifying authorization code...');
    const res = await window.api.youtubeVerifyCode(oauthCode);
    if (res.success) {
      setUploadStatus('Authenticated successfully! YouTube uploading enabled.');
      setAuthUrl('');
      setOauthCode('');
      loadData();
    } else {
      setUploadStatus(`Error: ${res.error}`);
    }
  };

  const handleUploadYoutube = async () => {
    if (!window.api) return;
    if (!publishForm.videoPath) {
      alert('Please specify a video file path!');
      return;
    }
    setUploadStatus('Uploading video to YouTube...');
    const res = await window.api.youtubeUpload({
      videoPath: publishForm.videoPath,
      title: publishForm.title,
      description: publishForm.description,
      tags: publishForm.tags,
      privacyStatus: publishForm.privacyStatus
    });

    if (res.success) {
      setUploadStatus(`Upload successful! Video ID: ${res.videoId}`);
    } else {
      setUploadStatus(`Upload failed: ${res.error}`);
    }
  };

  const toggleDaemon = async () => {
    if (window.api) {
      const res = await window.api.toggleStartupDaemon(!daemonEnabled);
      if (res.success) {
        setDaemonEnabled(res.enabled);
      }
    }
  };

  const saveSettings = async (newSettings) => {
    if (window.api) {
      await window.api.saveSettings(newSettings);
      loadData();
      alert('Settings saved!');
    }
  };

  // Calendar Helpers (Month Layout)
  const changeMonth = (offset) => {
    const next = new Date(currentDate.getFullYear(), currentDate.getMonth() + offset, 1);
    setCurrentDate(next);
  };

  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();
  const monthName = currentDate.toLocaleString('default', { month: 'long' });

  // Generate days in month (padded)
  const firstDayIndex = new Date(year, month, 1).getDay();
  const prevMonthLastDate = new Date(year, month, 0).getDate();
  const totalDays = new Date(year, month + 1, 0).getDate();

  const calendarDays = [];
  for (let i = firstDayIndex - 1; i >= 0; i--) {
    calendarDays.push({ day: prevMonthLastDate - i, isCurrentMonth: false, dateStr: '' });
  }
  for (let i = 1; i <= totalDays; i++) {
    const mStr = String(month + 1).padStart(2, '0');
    const dStr = String(i).padStart(2, '0');
    calendarDays.push({ day: i, isCurrentMonth: true, dateStr: `${year}-${mStr}-${dStr}` });
  }

  return (
    <div className="app-container">
      {/* Top Banner Navigation */}
      <header className="app-header">
        <div className="app-logo">
          <Sparkles className="text-purple-400" style={{ color: '#66fcf1' }} />
          <span>Content Command Center</span>
        </div>
        <nav className="app-nav">
          <div className={`nav-item ${activeTab === 'workspace' ? 'active' : ''}`} onClick={() => setActiveTab('workspace')}>
            <Sparkles size={16} /> Workspace Dock
          </div>
          <div className={`nav-item ${activeTab === 'calendar' ? 'active' : ''}`} onClick={() => setActiveTab('calendar')}>
            <CalendarIcon size={16} /> Scheduler Grid
          </div>
          <div className={`nav-item ${activeTab === 'library' ? 'active' : ''}`} onClick={() => setActiveTab('library')}>
            <BookOpen size={16} /> Content Library
          </div>
          <div className={`nav-item ${activeTab === 'settings' ? 'active' : ''}`} onClick={() => setActiveTab('settings')}>
            <Settings size={16} /> Settings
          </div>
        </nav>
      </header>

      {/* Main Workspace Section */}
      <main style={{ flex: 1, overflow: 'hidden' }}>
        {activeTab === 'workspace' && (
          <div className="workspace-container" style={{ display: 'grid', gridTemplateColumns: '1fr 380px', height: '100%', padding: '16px', gap: '16px' }}>
            
            {/* Zone A: AI Tab Dock (Main Workspace Area) */}
            <div className="split-pane glass-panel">
              <div className="panel-header" style={{ borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px' }}>
                <div style={{ display: 'flex', gap: '6px', overflowX: 'auto' }}>
                  {openAiTabs.map(tab => (
                    <div 
                      key={tab.id}
                      onClick={() => setActiveAiTabId(tab.id)}
                      style={{
                        padding: '6px 12px',
                        cursor: 'pointer',
                        borderRadius: '6px',
                        fontSize: '13px',
                        fontWeight: 600,
                        background: activeAiTabId === tab.id ? 'var(--accent-primary)' : 'rgba(255,255,255,0.05)',
                        color: '#fff',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px'
                      }}
                    >
                      <span>{tab.name}</span>
                      <X size={12} style={{ color: '#ff4d4d' }} onClick={(e) => { e.stopPropagation(); closeAiTab(tab.id); }} />
                    </div>
                  ))}
                </div>
                <div style={{ display: 'flex', gap: '5px' }}>
                  {AI_SERVICES.map(s => (
                    <button 
                      key={s.id} 
                      onClick={() => openAiService(s)}
                      style={{ padding: '4px 8px', fontSize: '11px', background: 'transparent', border: '1px solid var(--border-color)', borderRadius: '4px', color: '#fff', cursor: 'pointer' }}
                    >
                      + {s.name}
                    </button>
                  ))}
                </div>
              </div>

              {/* Webviews */}
              <div style={{ flex: 1, position: 'relative', background: '#0e1017' }}>
                {openAiTabs.map(tab => (
                  <div key={tab.id} style={{ display: activeAiTabId === tab.id ? 'block' : 'none', width: '100%', height: '100%' }}>
                    <webview 
                      src={tab.url}
                      partition={tab.partition}
                      style={{ width: '100%', height: '100%', border: 'none' }}
                      useragent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                    />
                  </div>
                ))}
                {openAiTabs.length === 0 && (
                  <div style={{ display: 'flex', height: '100%', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
                    <Sparkles size={48} />
                    <p style={{ marginTop: '10px' }}>No tabs currently active. Select an AI service above to get started.</p>
                  </div>
                )}
              </div>
            </div>

            {/* Zone C: Publish Console (Right Sidebar Panel) */}
            <div className="split-pane glass-panel">
              <div className="panel-header">
                <span>Zone C: Publish Console</span>
                <Video size={16} style={{ color: 'var(--accent-danger)' }} />
              </div>
              <div className="panel-body">
                <div className="form-group">
                  <label>Publish Destination</label>
                  <select value={publishPlatform} onChange={(e) => setPublishPlatform(e.target.value)}>
                    <option value="youtube">YouTube (Direct Upload)</option>
                    <option value="reddit">Reddit (Side-by-Side Copy)</option>
                    <option value="instagram">Instagram (Side-by-Side Copy)</option>
                    <option value="twitter">X / Twitter (Side-by-Side Copy)</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>Title / Post Header</label>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <input 
                      type="text" 
                      value={publishForm.title} 
                      onChange={(e) => setPublishForm({ ...publishForm, title: e.target.value })} 
                    />
                    <button className="btn btn-secondary" style={{ padding: '8px' }} onClick={() => navigator.clipboard.writeText(publishForm.title)}>
                      <Copy size={14} />
                    </button>
                  </div>
                </div>

                <div className="form-group">
                  <label>Description / Caption</label>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <textarea 
                      value={publishForm.description} 
                      onChange={(e) => setPublishForm({ ...publishForm, description: e.target.value })} 
                      style={{ minHeight: '80px' }}
                    />
                    <button className="btn btn-secondary" style={{ padding: '8px' }} onClick={() => navigator.clipboard.writeText(publishForm.description)}>
                      <Copy size={14} />
                    </button>
                  </div>
                </div>

                {publishPlatform === 'youtube' ? (
                  <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    <div className="form-group">
                      <label>Video File Path</label>
                      <input 
                        type="text" 
                        placeholder="e.g. C:\uploads\video.mp4" 
                        value={publishForm.videoPath} 
                        onChange={(e) => setPublishForm({ ...publishForm, videoPath: e.target.value })}
                      />
                    </div>
                    <div className="form-group">
                      <label>Tags</label>
                      <input 
                        type="text" 
                        value={publishForm.tags} 
                        onChange={(e) => setPublishForm({ ...publishForm, tags: e.target.value })}
                      />
                    </div>
                    <div className="form-group">
                      <label>Privacy</label>
                      <select value={publishForm.privacyStatus} onChange={(e) => setPublishForm({ ...publishForm, privacyStatus: e.target.value })}>
                        <option value="private">Private</option>
                        <option value="unlisted">Unlisted</option>
                        <option value="public">Public</option>
                      </select>
                    </div>

                    {settings.youtubeOauth?.clientId ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', background: 'var(--bg-secondary)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                        {authUrl && (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                            <a href="#" onClick={(e) => { e.preventDefault(); if (window.api) shell.openExternal(authUrl); }} style={{ color: 'var(--accent-primary)', fontSize: '12px', textDecoration: 'underline' }}>
                              Authenticate in Chrome Browser
                            </a>
                            <input 
                              type="text" 
                              placeholder="Verification code" 
                              value={oauthCode} 
                              onChange={(e) => setOauthCode(e.target.value)} 
                            />
                            <button className="btn btn-primary" onClick={handleVerifyCode}>Verify</button>
                          </div>
                        )}
                        {!authUrl && !settings.youtubeOauth?.tokens && (
                          <button className="btn btn-secondary" onClick={handleGetAuthUrl}>Request Token</button>
                        )}
                        {settings.youtubeOauth?.tokens && (
                          <button className="btn btn-primary" onClick={handleUploadYoutube}>
                            <Upload size={16} /> Upload Video
                          </button>
                        )}
                      </div>
                    ) : (
                      <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Configure YouTube credentials in Settings.</span>
                    )}
                    {uploadStatus && <div style={{ fontSize: '12px', color: 'var(--accent-info)', marginTop: '4px' }}>{uploadStatus}</div>}
                  </div>
                ) : (
                  <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    <div className="form-group">
                      <label>Tags & Hashtags</label>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <input 
                          type="text" 
                          placeholder="#ev #news" 
                          value={publishForm.hashtags} 
                          onChange={(e) => setPublishForm({ ...publishForm, hashtags: e.target.value })}
                        />
                        <button className="btn btn-secondary" style={{ padding: '8px' }} onClick={() => navigator.clipboard.writeText(publishForm.hashtags)}>
                          <Copy size={14} />
                        </button>
                      </div>
                    </div>
                    <button className="btn btn-secondary" onClick={() => {
                      const urlMap = {
                        reddit: 'https://www.reddit.com/r/submit',
                        instagram: 'https://www.instagram.com/',
                        twitter: 'https://x.com/'
                      };
                      openAiService({ id: publishPlatform, name: publishPlatform.toUpperCase(), url: urlMap[publishPlatform], partition: `persist:${publishPlatform}` });
                    }}>
                      Open {publishPlatform.toUpperCase()} side-by-side
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Zone B: Calendar & Reminders */}
        {activeTab === 'calendar' && (
          <div className="fade-in" style={{ display: 'grid', gridTemplateColumns: '1fr 340px', height: '100%', padding: '16px', gap: '16px' }}>
            <div className="glass-panel" style={{ padding: '16px', display: 'flex', flexDirection: 'column' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <h3 style={{ fontSize: '18px', display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <CalendarIcon style={{ color: 'var(--accent-primary)' }} />
                  {monthName} {year}
                </h3>
                <div style={{ display: 'flex', gap: '6px' }}>
                  <button className="btn btn-secondary" onClick={() => changeMonth(-1)}><ChevronLeft size={16} /></button>
                  <button className="btn btn-secondary" onClick={() => changeMonth(1)}><ChevronRight size={16} /></button>
                </div>
              </div>

              {/* Month Grid */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: '8px', flex: 1 }}>
                {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(d => (
                  <div key={d} style={{ textAlign: 'center', fontWeight: 'bold', fontSize: '12px', paddingBottom: '6px', color: 'var(--text-secondary)' }}>{d}</div>
                ))}
                {calendarDays.map((c, idx) => {
                  const items = calendar.filter(item => item.date === c.dateStr);
                  const isSelected = c.dateStr === selectedDate;
                  return (
                    <div 
                      key={idx}
                      onClick={() => c.dateStr && setSelectedDate(c.dateStr)}
                      style={{
                        background: isSelected ? 'rgba(102, 252, 241, 0.15)' : c.isCurrentMonth ? 'rgba(255,255,255,0.02)' : 'transparent',
                        border: isSelected ? '1px solid var(--accent-primary)' : '1px solid var(--border-color)',
                        borderRadius: '6px',
                        padding: '6px',
                        cursor: c.dateStr ? 'pointer' : 'default',
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'space-between',
                        minHeight: '60px',
                        opacity: c.isCurrentMonth ? 1 : 0.25
                      }}
                    >
                      <span style={{ fontSize: '12px', fontWeight: 600 }}>{c.day}</span>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', marginTop: '4px' }}>
                        {items.slice(0, 2).map(item => (
                          <div 
                            key={item.id} 
                            style={{ 
                              fontSize: '9px', 
                              padding: '2px 4px', 
                              borderRadius: '3px', 
                              background: item.status === 'Posted' ? 'rgba(76, 175, 80, 0.2)' : 'rgba(255, 152, 0, 0.2)',
                              color: item.status === 'Posted' ? '#81c784' : '#ffb74d',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                              overflow: 'hidden'
                            }}
                          >
                            {item.title}
                          </div>
                        ))}
                        {items.length > 2 && <span style={{ fontSize: '8px', color: 'var(--text-muted)' }}>+{items.length - 2} more</span>}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Scheduling Form Panel */}
            <div className="glass-panel" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ fontWeight: 600, fontSize: '15px' }}>Schedule Content: {selectedDate}</div>
              
              <form onSubmit={handleSaveCalendarEntry} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div className="form-group">
                  <label>Title</label>
                  <input 
                    type="text" 
                    placeholder="Enter post title" 
                    value={newCalendarEntry.title}
                    onChange={(e) => setNewCalendarEntry({ ...newCalendarEntry, title: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label>Note / Outline</label>
                  <textarea 
                    placeholder="Paste draft details here" 
                    value={newCalendarEntry.note}
                    onChange={(e) => setNewCalendarEntry({ ...newCalendarEntry, note: e.target.value })}
                    style={{ minHeight: '80px' }}
                  />
                </div>
                <div className="form-group">
                  <label>Attach File Path</label>
                  <input 
                    type="text" 
                    placeholder="C:\path\to\file.mp4" 
                    value={newCalendarEntry.filePath}
                    onChange={(e) => setNewCalendarEntry({ ...newCalendarEntry, filePath: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label>Platform</label>
                  <select value={newCalendarEntry.platform} onChange={(e) => setNewCalendarEntry({ ...newCalendarEntry, platform: e.target.value })}>
                    <option value="YouTube">YouTube</option>
                    <option value="Reddit">Reddit</option>
                    <option value="Instagram">Instagram</option>
                    <option value="X">X / Twitter</option>
                  </select>
                </div>

                <button type="submit" className="btn btn-primary">Schedule Item</button>
              </form>

              {/* Day's Scheduled Items */}
              <div style={{ flex: 1, overflowY: 'auto', marginTop: '10px' }}>
                <div style={{ fontWeight: 600, fontSize: '13px', borderBottom: '1px solid var(--border-color)', paddingBottom: '6px', marginBottom: '8px' }}>Scheduled for this day:</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {calendar.filter(item => item.date === selectedDate).map(item => (
                    <div key={item.id} style={{ padding: '8px', background: 'var(--bg-secondary)', borderRadius: '6px', borderLeft: `3px solid ${item.status === 'Posted' ? 'var(--accent-success)' : 'var(--accent-warning)'}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontWeight: 600, fontSize: '13px' }}>{item.title}</span>
                        <div style={{ display: 'flex', gap: '4px' }}>
                          <button className="btn btn-secondary" style={{ padding: '2px 6px', fontSize: '10px' }} onClick={() => togglePostedStatus(item)}>
                            {item.status === 'Posted' ? 'Posted' : 'Mark'}
                          </button>
                          <button className="btn btn-danger" style={{ padding: '2px 4px' }} onClick={() => handleDeleteCalendarItem(item.id)}>
                            <Trash2 size={12} />
                          </button>
                        </div>
                      </div>
                      <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '4px' }}>{item.platform}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Zone D: Content Library */}
        {activeTab === 'library' && (
          <div className="fade-in" style={{ padding: '24px', overflowY: 'auto', height: '100%' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
              <h2>Zone D: Content Library Archive</h2>
              <div style={{ width: '300px' }}>
                <input 
                  type="text" 
                  placeholder="Search metadata archive..." 
                  onChange={(e) => {
                    const q = e.target.value.toLowerCase();
                    if (window.api) {
                      window.api.getCalendar().then(all => {
                        setCalendar(all.filter(i => i.title.toLowerCase().includes(q) || (i.note || '').toLowerCase().includes(q)));
                      });
                    }
                  }} 
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '20px' }}>
              {calendar.map(item => (
                <div key={item.id} className="glass-panel" style={{ display: 'flex', flexDirection: 'column', height: '220px' }}>
                  <div className="panel-header" style={{ textTransform: 'none', display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ fontWeight: 700 }}>{item.title}</span>
                    <span className="badge" style={{ background: 'rgba(255,255,255,0.08)', color: '#66fcf1' }}>{item.platform}</span>
                  </div>
                  <div style={{ flex: 1, padding: '16px', fontSize: '13px', color: 'var(--text-secondary)', overflowY: 'auto' }}>
                    {item.note || 'No notes added.'}
                    {item.filePath && (
                      <div style={{ marginTop: '8px', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '11px', color: 'var(--accent-info)' }}>
                        <File size={12} /> {item.filePath}
                      </div>
                    )}
                  </div>
                  <div style={{ padding: '12px 16px', borderTop: '1px solid var(--border-color)', display: 'flex', gap: '8px', justifyContent: 'space-between', background: 'rgba(0,0,0,0.1)' }}>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Date: {item.date}</span>
                    <div style={{ display: 'flex', gap: '6px' }}>
                      <button className="btn btn-secondary" style={{ padding: '4px 8px', fontSize: '11px' }} onClick={() => handleLoadToPublish(item)}>
                        Load
                      </button>
                      <button className="btn btn-danger" style={{ padding: '4px 6px' }} onClick={() => handleDeleteCalendarItem(item.id)}>
                        <Trash2 size={12} />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
              {calendar.length === 0 && (
                <div style={{ gridColumn: '1/-1', textAlign: 'center', padding: '48px', color: 'var(--text-muted)' }}>
                  No content saved yet. Schedule content using the Scheduler Grid.
                </div>
              )}
            </div>
          </div>
        )}

        {/* Settings View */}
        {activeTab === 'settings' && (
          <div className="fade-in" style={{ padding: '24px', maxWidth: '680px', margin: '0 auto', overflowY: 'auto', height: '100%' }}>
            <h2>Settings & Configurations</h2>
            
            <div className="glass-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '20px', marginBottom: '20px', marginTop: '20px' }}>
              <h3>OS Background Reminders</h3>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontWeight: 600 }}>Enable Startup Daemon</div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Checks the database for unposted scheduled posts every day when Windows starts up.</div>
                </div>
                <button className={`btn ${daemonEnabled ? 'btn-danger' : 'btn-primary'}`} onClick={toggleDaemon}>
                  {daemonEnabled ? 'Disable' : 'Enable'}
                </button>
              </div>
            </div>

            <div className="glass-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <h3>YouTube Data API (OAuth2)</h3>
              <div className="form-group">
                <label>Client ID</label>
                <input 
                  type="text" 
                  value={settings.youtubeOauth?.clientId || ''} 
                  onChange={(e) => setSettings({ 
                    ...settings, 
                    youtubeOauth: { ...settings.youtubeOauth, clientId: e.target.value } 
                  })} 
                />
              </div>
              <div className="form-group">
                <label>Client Secret</label>
                <input 
                  type="password" 
                  value={settings.youtubeOauth?.clientSecret || ''} 
                  onChange={(e) => setSettings({ 
                    ...settings, 
                    youtubeOauth: { ...settings.youtubeOauth, clientSecret: e.target.value } 
                  })} 
                />
              </div>
              <div className="form-group">
                <label>Redirect URI</label>
                <input 
                  type="text" 
                  value={settings.youtubeOauth?.redirectUri || 'urn:ietf:wg:oauth:2.0:oob'} 
                  onChange={(e) => setSettings({ 
                    ...settings, 
                    youtubeOauth: { ...settings.youtubeOauth, redirectUri: e.target.value } 
                  })} 
                />
              </div>
              <button className="btn btn-primary" onClick={() => saveSettings(settings)}>
                Save OAuth Credentials
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}


