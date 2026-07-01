const fs = require('fs');
const path = require('path');

let userDataPath;
try {
  // If running inside Electron main process
  const { app } = require('electron');
  userDataPath = app.getPath('userData');
} catch (e) {
  // If running in standalone background daemon
  userDataPath = path.join(
    process.env.APPDATA || (process.platform === 'darwin' ? process.env.HOME + '/Library/Application Support' : process.env.HOME + '/.config'),
    'content-command-center'
  );
}

const dbPath = path.join(userDataPath, 'database.json');

// Ensure directories exist
if (!fs.existsSync(userDataPath)) {
  fs.mkdirSync(userDataPath, { recursive: true });
}

// Default Schema
const defaultDb = {
  ideas: [],
  calendar: [],
  settings: {
    youtubeOauth: null,
    publishDefaults: {
      tags: '',
      hashtags: '',
      description: ''
    }
  }
};

function readDb() {
  try {
    if (!fs.existsSync(dbPath)) {
      writeDb(defaultDb);
      return defaultDb;
    }
    const data = fs.readFileSync(dbPath, 'utf8');
    return JSON.parse(data);
  } catch (err) {
    console.error('Error reading database:', err);
    return defaultDb;
  }
}

function writeDb(data) {
  try {
    fs.writeFileSync(dbPath, JSON.stringify(data, null, 2), 'utf8');
  } catch (err) {
    console.error('Error writing database:', err);
  }
}

const db = {
  // Ideas
  getIdeas() {
    const data = readDb();
    return data.ideas || [];
  },
  saveIdea(idea) {
    const data = readDb();
    if (!data.ideas) data.ideas = [];
    
    if (idea.id) {
      const idx = data.ideas.findIndex(i => i.id === idea.id);
      if (idx !== -1) {
        data.ideas[idx] = { ...data.ideas[idx], ...idea, updatedAt: new Date().toISOString() };
      } else {
        data.ideas.push(idea);
      }
    } else {
      idea.id = 'idea_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
      idea.createdAt = new Date().toISOString();
      idea.updatedAt = new Date().toISOString();
      data.ideas.push(idea);
    }
    writeDb(data);
    return idea;
  },
  deleteIdea(id) {
    const data = readDb();
    data.ideas = (data.ideas || []).filter(i => i.id !== id);
    // Also remove calendar references if any
    data.calendar = (data.calendar || []).filter(c => c.contentId !== id);
    writeDb(data);
    return true;
  },

  // Calendar
  getCalendar() {
    const data = readDb();
    return data.calendar || [];
  },
  saveCalendarEntry(entry) {
    const data = readDb();
    if (!data.calendar) data.calendar = [];
    
    if (entry.id) {
      const idx = data.calendar.findIndex(c => c.id === entry.id);
      if (idx !== -1) {
        data.calendar[idx] = { ...data.calendar[idx], ...entry };
      } else {
        data.calendar.push(entry);
      }
    } else {
      entry.id = 'cal_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
      data.calendar.push(entry);
    }
    writeDb(data);
    return entry;
  },
  deleteCalendarEntry(id) {
    const data = readDb();
    data.calendar = (data.calendar || []).filter(c => c.id !== id);
    writeDb(data);
    return true;
  },

  // Settings
  getSettings() {
    const data = readDb();
    return data.settings || defaultDb.settings;
  },
  saveSettings(settings) {
    const data = readDb();
    data.settings = { ...data.settings, ...settings };
    writeDb(data);
    return data.settings;
  }
};

module.exports = db;
