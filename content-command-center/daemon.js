const { exec } = require('child_process');
const db = require('./db');

function checkReminders() {
  const calendar = db.getCalendar();
  const ideas = db.getIdeas();
  const todayStr = new Date().toISOString().split('T')[0];

  // Filter pending items due today or in the past
  const pendingItems = calendar.filter(item => {
    return item.date <= todayStr && !item.posted;
  });

  if (pendingItems.length > 0) {
    const titles = pendingItems.map(item => {
      const idea = ideas.find(i => i.id === item.contentId);
      return idea ? `• ${idea.title} (${item.platform})` : `• Scheduled Item (${item.platform})`;
    }).join('\n');

    sendNotification(pendingItems.length, titles);
  }
}

function sendNotification(count, itemsText) {
  // Use PowerShell to trigger a modern, beautiful system popup/toast on Windows
  const escapedMessage = `You have ${count} pending content post(s) scheduled for today or earlier that are not yet marked as posted:\n\n${itemsText}`.replace(/"/g, '`"');
  
  const psCommand = `
[void] [System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms');
[System.Windows.Forms.MessageBox]::Show("${escapedMessage}", "Content Command Center Reminder", 0, 64)
`;

  exec(`powershell -Command "${psCommand.trim().replace(/\n/g, ' ')}"`, (err) => {
    if (err) {
      console.error('Failed to trigger Windows notification:', err);
    }
  });
}

// Run immediately
checkReminders();
