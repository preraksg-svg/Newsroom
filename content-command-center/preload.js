const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('api', {
  // DB Operations
  getIdeas: () => ipcRenderer.invoke('db:getIdeas'),
  saveIdea: (idea) => ipcRenderer.invoke('db:saveIdea', idea),
  deleteIdea: (id) => ipcRenderer.invoke('db:deleteIdea', id),
  
  getCalendar: () => ipcRenderer.invoke('db:getCalendar'),
  saveCalendarEntry: (entry) => ipcRenderer.invoke('db:saveCalendarEntry', entry),
  deleteCalendarEntry: (id) => ipcRenderer.invoke('db:deleteCalendarEntry', id),
  
  getSettings: () => ipcRenderer.invoke('db:getSettings'),
  saveSettings: (settings) => ipcRenderer.invoke('db:saveSettings', settings),

  // YouTube OAuth and Upload Operations
  youtubeAuthUrl: () => ipcRenderer.invoke('yt:getAuthUrl'),
  youtubeVerifyCode: (code) => ipcRenderer.invoke('yt:verifyCode', code),
  youtubeUpload: (videoData) => ipcRenderer.invoke('yt:uploadVideo', videoData),

  // Background Startup Daemon Control
  toggleStartupDaemon: (enable) => ipcRenderer.invoke('sys:toggleDaemon', enable),
  checkDaemonStatus: () => ipcRenderer.invoke('sys:checkDaemon'),

  // External webview helper to paste outline/draft to webviews
  sendToWebview: (webviewId, text) => ipcRenderer.send('webview:sendData', webviewId, text)
});
