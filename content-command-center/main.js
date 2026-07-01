const { app, BrowserWindow, ipcMain, shell, Tray, Menu, nativeImage } = require('electron');
const path = require('path');
const fs = require('fs');
const { google } = require('googleapis');
const db = require('./db');

let mainWindow;
let tray = null;
let isQuitting = false;

function checkScheduledEntries() {
  const entries = db.getCalendar();
  const todayStr = new Date().toISOString().split('T')[0];
  
  // Filter scheduled entries due today or in the past
  const overdue = entries.filter(e => e.date <= todayStr && e.status === 'Scheduled');
  
  console.log(`[Scheduler Check] Ran at ${new Date().toISOString()}`);
  console.log(`[Scheduler Check] Found ${overdue.length} overdue scheduled entries.`);
  
  overdue.forEach(e => {
    console.log(`[Scheduler Alert] Title: "${e.title}" | Scheduled Date: ${e.date} | Note: "${e.note || ''}"`);
    // Electron Notification API call will be inserted here
  });
}

function createTray() {
  // 1x1 transparent PNG base64 icon
  const iconBase64 = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=';
  const trayIcon = nativeImage.createFromDataURL(iconBase64);
  
  tray = new Tray(trayIcon);
  
  const contextMenu = Menu.buildFromTemplate([
    { label: 'Open Content Command Center', click: () => mainWindow.show() },
    { type: 'separator' },
    { label: 'Quit App', click: () => {
        isQuitting = true;
        app.quit();
      }
    }
  ]);
  
  tray.setToolTip('Content Command Center');
  tray.setContextMenu(contextMenu);
  tray.on('click', () => {
    mainWindow.show();
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      webviewTag: true
    },
    title: 'Content Command Center',
    autoHideMenuBar: true
  });

  const distIndexExists = fs.existsSync(path.join(__dirname, 'dist', 'index.html'));
  
  if (!distIndexExists && (process.env.NODE_ENV === 'development' || !app.isPackaged)) {
    mainWindow.loadURL('http://localhost:5173');
  } else {
    mainWindow.loadFile(path.join(__dirname, 'dist', 'index.html'));
  }

  // Intercept close event to hide window instead of quitting (for background running)
  mainWindow.on('close', (event) => {
    const settings = db.getSettings();
    if (!isQuitting && settings.backgroundRemindersEnabled) {
      event.preventDefault();
      mainWindow.hide();
    }
  });
}

app.whenReady().then(() => {
  createWindow();
  createTray();

  // Run the background check immediately on startup
  checkScheduledEntries();

  // Run the background check every 24 hours
  setInterval(checkScheduledEntries, 24 * 60 * 60 * 1000);

  app.on('activate', function () {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', function () {
  const settings = db.getSettings();
  if (process.platform !== 'darwin' && !settings.backgroundRemindersEnabled) {
    app.quit();
  }
});

// IPC DB Handlers
ipcMain.handle('db:getIdeas', () => db.getIdeas());
ipcMain.handle('db:saveIdea', (event, idea) => db.saveIdea(idea));
ipcMain.handle('db:deleteIdea', (event, id) => db.deleteIdea(id));

ipcMain.handle('db:getCalendar', () => db.getCalendar());
ipcMain.handle('db:saveCalendarEntry', (event, entry) => db.saveCalendarEntry(entry));
ipcMain.handle('db:deleteCalendarEntry', (event, id) => db.deleteCalendarEntry(id));

ipcMain.handle('db:getSettings', () => db.getSettings());
ipcMain.handle('db:saveSettings', (event, settings) => db.saveSettings(settings));

// OAuth Client Helper
function getOAuth2Client(settings) {
  const ytSettings = settings.youtubeOauth || {};
  const { clientId, clientSecret, redirectUri } = ytSettings;
  if (!clientId || !clientSecret) {
    throw new Error('OAuth2 Client credentials not configured in settings.');
  }
  return new google.auth.OAuth2(
    clientId,
    clientSecret,
    redirectUri || 'urn:ietf:wg:oauth:2.0:oob'
  );
}

// YouTube API Handlers
ipcMain.handle('yt:getAuthUrl', async () => {
  try {
    const settings = db.getSettings();
    const oauth2Client = getOAuth2Client(settings);
    const authUrl = oauth2Client.generateAuthUrl({
      access_type: 'offline',
      scope: ['https://www.googleapis.com/auth/youtube.upload'],
      prompt: 'consent'
    });
    return { success: true, url: authUrl };
  } catch (error) {
    return { success: false, error: error.message };
  }
});

ipcMain.handle('yt:verifyCode', async (event, code) => {
  try {
    const settings = db.getSettings();
    const oauth2Client = getOAuth2Client(settings);
    const { tokens } = await oauth2Client.getToken(code);
    
    const ytOauth = settings.youtubeOauth || {};
    ytOauth.tokens = tokens;
    db.saveSettings({ youtubeOauth: ytOauth });
    
    return { success: true };
  } catch (error) {
    return { success: false, error: error.message };
  }
});

ipcMain.handle('yt:uploadVideo', async (event, { videoPath, title, description, tags, privacyStatus }) => {
  try {
    const settings = db.getSettings();
    const oauth2Client = getOAuth2Client(settings);
    
    const tokens = settings.youtubeOauth?.tokens;
    if (!tokens) {
      throw new Error('Authentication required. Please authenticate first.');
    }
    
    oauth2Client.setCredentials(tokens);
    
    const youtube = google.youtube({ version: 'v3', auth: oauth2Client });
    
    if (!fs.existsSync(videoPath)) {
      throw new Error(`File not found at path: ${videoPath}`);
    }
    
    const media = {
      body: fs.createReadStream(videoPath)
    };
    
    const response = await youtube.videos.insert({
      part: 'snippet,status',
      requestBody: {
        snippet: {
          title: title,
          description: description,
          tags: tags ? tags.split(',').map(t => t.trim()) : []
        },
        status: {
          privacyStatus: privacyStatus || 'private'
        }
      },
      media: media
    });
    
    return { success: true, videoId: response.data.id };
  } catch (error) {
    return { success: false, error: error.message };
  }
});

// Windows Login Item settings
ipcMain.handle('sys:toggleDaemon', (event, enable) => {
  try {
    app.setLoginItemSettings({
      openAtLogin: enable,
      openAsHidden: true, // Start hidden in background on login
      path: app.getPath('exe'),
      args: ['--hidden']
    });
    
    db.saveSettings({ backgroundRemindersEnabled: enable });
    return { success: true, enabled: enable };
  } catch (error) {
    return { success: false, error: error.message };
  }
});

ipcMain.handle('sys:checkDaemon', () => {
  const settings = db.getSettings();
  return { enabled: !!settings.backgroundRemindersEnabled };
});

