let globalRecords = [];
let isUTC = false;
let lastIngestTime = Date.now();

document.addEventListener('DOMContentLoaded', () => {
    fetchArticles();
    
    // Start Real-time clock
    setInterval(updateLiveClock, 1000);
    setInterval(updateSecondsCounter, 1000);
    updateLiveClock();
    
    // Poll the UI every 15 seconds so new drafts appear magically
    setInterval(fetchArticles, 15000);

    document.getElementById('btn-fetch').addEventListener('click', async () => {
        const btn = document.getElementById('btn-fetch');
        btn.innerHTML = 'INGESTING... <div style="display:inline-block; font-size:10px;">⏳</div>';
        try {
            await fetch('/api/ingest', { method: 'POST' });
        } catch (e) {
            console.error('Failed to trigger fetch:', e);
        }
        setTimeout(() => {
            btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" class="search-icon" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg> FORCE INGEST';
        }, 2000);
    });

    document.getElementById('btn-publish').addEventListener('click', async () => {
        const btn = document.getElementById('btn-publish');
        const origText = btn.innerHTML;
        btn.innerHTML = 'DEPLOYING... <div style="display:inline-block; font-size:10px;">⏳</div>';
        try {
            await fetch('/api/publish', { method: 'POST' });
            fetchArticles();
        } catch (e) {
            console.error('Failed to trigger publish:', e);
        }
        setTimeout(() => {
            btn.innerHTML = origText;
        }, 2000);
    });
});

function updateLiveClock() {
    const el = document.getElementById('live-time');
    if(el) {
        const now = new Date();
        const tz = isUTC ? 'UTC' : 'Asia/Kolkata';
        el.innerText = now.toLocaleTimeString('en-US', { timeZone: tz, hour12: false });
    }
}

function updateSecondsCounter() {
    const el = document.getElementById('last-updated');
    if(el) {
        const diff = Math.floor((Date.now() - lastIngestTime) / 1000);
        el.innerText = `Last updated ${diff}s ago`;
    }
}

window.toggleTimezone = function() {
    isUTC = !isUTC;
    document.getElementById('tz-toggle').innerText = isUTC ? 'UTC' : 'IST';
    updateLiveClock();
}

async function fetchArticles() {
    try {
        const res = await fetch('/api/articles');
        const json = await res.json();
        if (json.success && json.data) {
            lastIngestTime = Date.now();
            renderDashboard(json.data);
        }
    } catch (e) {
        console.error('Error fetching articles:', e);
    }
}

function renderDashboard(records) {
    globalRecords = records;
    const listDrafts = document.getElementById('list-drafts');
    const listApproved = document.getElementById('list-approved');
    const listPublished = document.getElementById('list-published');
    const listRejected = document.getElementById('list-rejected');

    let draftsHtml = '';
    let approvedHtml = '';
    let publishedHtml = '';
    let rejectedHtml = '';
    let countDrafts = 0;
    
    // Update Breaking News Hero if we have records
    if(records.length > 0) {
        const top = records[0];
        const hTitle = top.fields['SEO Headline'] || top.fields['Title'] || 'Untitled';
        const docTop = document.getElementById('top-headline');
        if(docTop) docTop.innerText = hTitle;
    }

    records.forEach(r => {
        const fields = r.fields || {};
        const status = fields['Status'] || 'Draft';
        const title = fields['SEO Headline'] || fields['Title'] || 'Untitled';
        const summary = fields['Short Summary'] || 'Waiting for AI processing...';
        const wpLink = fields['WordPress URL'] || null;
        const errorMsg = fields['Error Message'] || null;
        
        const publisher = fields['Publisher'] || 'System';
        const finalScore = fields['Final Score'] ? parseFloat(fields['Final Score']).toFixed(1) : 'N/A';
        const priority = fields['Priority'] || 'Normal';
        
        let dateString = fields['Published Date'] || r.createdTime || '';
        if(dateString) {
            const d = new Date(dateString);
            if(!isNaN(d)) dateString = d.toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
        }

        // Priority rendering
        let pColor = '#aaa';
        if(priority === 'Highest') pColor = 'var(--c-magenta)';
        if(priority === 'High') pColor = 'var(--c-cyan)';
        
        // Score color
        let sColor = '#fff';
        if(finalScore >= 85) sColor = 'var(--c-green)';
        else if (finalScore < 70) sColor = 'var(--c-red)';

        let cardHtml = `
            <div class="card" onclick="openModal('${r.id}')">
                <div class="card-title">${title} <span style="font-family: var(--font-data); font-size: 0.65rem; color: ${pColor}; border: 1px solid ${pColor}; padding: 2px 6px; border-radius: 4px; vertical-align: middle; margin-left: 5px;">${priority.toUpperCase()}</span></div>
        `;

        // Wait string
        const waitStr = `Score: <b style="color:${sColor}">${finalScore}</b>`;

        if (status === 'Draft' || status === 'Review' || status === 'Auto-Draft') {
            countDrafts++;
            cardHtml += `
                <div class="card-source">${summary}</div>
                <div class="card-footer" style="margin-top:auto;">
                    <span>${waitStr}</span>
                    <div>
                        <button class="view-btn" onclick="event.stopPropagation(); openModal('${r.id}')">INSPECT</button>
                        <button class="view-btn" style="border-color:var(--c-cyan); color:var(--c-cyan); margin-left: 5px;" onclick="event.stopPropagation(); approveArticle('${r.id}')">DEPLOY</button>
                        <button class="view-btn" style="border-color:var(--c-magenta); color:var(--c-magenta); margin-left: 5px;" onclick="event.stopPropagation(); rejectArticle('${r.id}')">HALT</button>
                    </div>
                </div>
            `;
        } else {
             // For left calendar sidebar items
             cardHtml += `
                <div class="card-footer">
                    <span>${dateString}</span>
                    <button class="view-btn" onclick="event.stopPropagation(); openModal('${r.id}')">VIEW</button>
                </div>
            `;
        }
        
        cardHtml += `</div>`;

        if (status === 'Draft' || status === 'Review' || status === 'Auto-Draft') {
            const createdDate = new Date(story.created_at ? story.created_at.replace(' ', 'T') : 0);
            const now = new Date();
            const hoursDiff = (now - createdDate) / (1000 * 60 * 60);
            if (hoursDiff <= 48) {
                draftsHtml += cardHtml;
            }
        }
        else if (status === 'Approved') approvedHtml += cardHtml;
        else if (status === 'Rejected') rejectedHtml += cardHtml;
        else publishedHtml += cardHtml;
    });

    listDrafts.innerHTML = draftsHtml || '<p class="terminal-loader">No pending intelligence signals...</p>';
    listApproved.innerHTML = approvedHtml || '<p class="terminal-loader">No verified signals...</p>';
    listPublished.innerHTML = publishedHtml || '<p class="terminal-loader">Archive empty...</p>';
    if (listRejected) listRejected.innerHTML = rejectedHtml || '<p class="terminal-loader">Wipe complete...</p>';
    
    document.getElementById('draft-count').innerText = `${countDrafts} PENDING`;
}

window.approveArticle = async function(id) {
    const record = globalRecords.find(r => r.id === id);
    if(record) {
        const fields = record.fields;
        if (!fields['Meta Title'] || !fields['Meta Description'] || !fields['SEO Headline'] || !fields['AI Article HTML']) {
            alert("Validation Error: Missing SEO Headline, Meta Tags, or HTML Body! Please switch to Edit Mode and fill these out before approving.");
            return;
        }
    }
    
    try {
        const res = await fetch(`/api/approve/${id}`, { method: 'POST' });
        const json = await res.json();
        if(!json.success) {
            alert("Approval Failed: " + json.error);
        }
        // Refresh UI immediately
        fetchArticles();
    } catch (e) {
        console.error('Approval failed:', e);
    }
}

window.rejectArticle = async function(id) {
    try {
        await fetch(`/api/reject/${id}`, { method: 'POST' });
        fetchArticles();
    } catch (e) {
        console.error('Reject failed:', e);
    }
}

window.openModal = function(id) {
    const record = globalRecords.find(r => r.id === id);
    if(!record) return;
    const fields = record.fields;
    
    document.getElementById('modal-meta-title').innerText = fields['Meta Title'] || 'N/A';
    document.getElementById('meta-title-count').innerText = `(${(fields['Meta Title'] || '').length}/60 chars)`;
    
    document.getElementById('modal-meta-desc').innerText = fields['Meta Description'] || 'N/A';
    document.getElementById('meta-desc-count').innerText = `(${(fields['Meta Description'] || '').length}/155 chars)`;
    
    document.getElementById('modal-meta-keywords').innerText = fields['SEO Keywords'] || 'N/A';
    
    document.getElementById('modal-title').innerText = fields['SEO Headline'] || fields['Title'] || 'Untitled';
    
    // We retain white-space for original text since it lacks HTML tags usually.
    document.getElementById('modal-original').innerHTML = `<div style="white-space: pre-wrap;">${fields['Original Content'] || 'No original content attached.'}</div>`;
    
    // AI has full native HTML
    document.getElementById('modal-ai').innerHTML = fields['AI Article HTML'] || '<p>No AI draft created.</p>';
    
    // Fill Editor Fields
    currentEditId = id;
    document.getElementById('edit-headline').value = fields['SEO Headline'] || fields['Title'] || '';
    document.getElementById('edit-summary').value = fields['Short Summary'] || '';
    document.getElementById('edit-meta-title').value = fields['Meta Title'] || '';
    document.getElementById('edit-meta-desc').value = fields['Meta Description'] || '';
    document.getElementById('edit-keywords').value = fields['SEO Keywords'] || '';
    document.getElementById('edit-html-body').value = fields['AI Article HTML'] || '';
    
    let htmlContent = document.getElementById('edit-html-body').value;
    let match = htmlContent.match(/https:\/\/image\.pollinations\.ai\/prompt\/([^?&'\"]+)/);
    if(match) {
        document.getElementById('edit-image-prompt').value = decodeURIComponent(match[1]);
    } else {
        document.getElementById('edit-image-prompt').value = '';
    }
    
    // Reset Edit Mode State
    document.getElementById('modal-ai-view').classList.remove('hidden');
    document.getElementById('modal-ai-edit').classList.add('hidden');
    document.getElementById('modal-edit-toggle-btn').innerText = 'Enable Editor ✏️';

    const approveBtn = document.getElementById('modal-approve-btn');
    if(fields['Status'] === 'Draft') {
        approveBtn.style.display = 'inline-flex';
        approveBtn.onclick = function() {
            approveArticle(id);
            closeModal();
        };
    } else {
        approveBtn.style.display = 'none';
    }
    
    document.getElementById('article-modal').classList.remove('hidden');
}

window.closeModal = function() {
    document.getElementById('article-modal').classList.add('hidden');
}

let currentEditId = null;

window.toggleEditMode = function() {
    const viewEl = document.getElementById('modal-ai-view');
    const editEl = document.getElementById('modal-ai-edit');
    const btn = document.getElementById('modal-edit-toggle-btn');
    
    if (viewEl.classList.contains('hidden')) {
        viewEl.classList.remove('hidden');
        editEl.classList.add('hidden');
        btn.innerText = 'Enable Editor ✏️';
    } else {
        viewEl.classList.add('hidden');
        editEl.classList.remove('hidden');
        btn.innerText = 'Close Editor ✕';
    }
}

window.saveEdits = async function() {
    if(!currentEditId) return;
    
    const payload = {
        seo_headline: document.getElementById('edit-headline').value,
        short_summary: document.getElementById('edit-summary').value,
        html_body: document.getElementById('edit-html-body').value,
        meta_title: document.getElementById('edit-meta-title').value,
        meta_description: document.getElementById('edit-meta-desc').value,
        seo_keywords: document.getElementById('edit-keywords').value
    };
    
    try {
        const res = await fetch(`/api/edit/${currentEditId}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        const json = await res.json();
        if(json.success) {
            alert("Changes Saved! Review the updated draft.");
            fetchArticles(); // reload data
            
            // Re-render modal in background by finding updated record via fetch delay or doing a dirty hack
            setTimeout(() => {
                const updatedRec = globalRecords.find(r => r.id === currentEditId);
                if(updatedRec) openModal(currentEditId);
            }, 500);
        } else {
            alert("Error saving: " + json.error);
        }
    } catch(e) {
        console.error(e);
        alert("Failed to save.");
    }
}

window.rollbackDraft = async function() {
    if(!currentEditId) return;
    if(!confirm("Are you sure you want to rollback to the original AI generated draft? All manual edits will be lost.")) return;
    
    try {
        const res = await fetch(`/api/rollback/${currentEditId}`, { method: 'POST' });
        const json = await res.json();
        if(json.success) {
            alert("Rollback successful.");
            fetchArticles();
            setTimeout(() => { openModal(currentEditId); toggleEditMode(); }, 500);
        } else {
            alert("Rollback error: " + json.error);
        }
    } catch(e) {
        console.error(e);
    }
}

window.promptAiEdit = async function(sectionName) {
    if(!currentEditId) return;
    
    const instr = prompt(`What do you want the AI to do to the '${sectionName}'?`);
    if(!instr) return;
    
    // determine content based on section
    let contentEl;
    if(sectionName === 'SEO Headline') contentEl = document.getElementById('edit-headline');
    if(sectionName === 'Short Summary') contentEl = document.getElementById('edit-summary');
    if(sectionName === 'Meta Title') contentEl = document.getElementById('edit-meta-title');
    if(sectionName === 'Meta Description') contentEl = document.getElementById('edit-meta-desc');
    if(sectionName === 'AI Article HTML') contentEl = document.getElementById('edit-html-body');
    
    if(!contentEl) return;
    
    const origVal = contentEl.value;
    contentEl.value = `[AI is editing... please wait]`;
    
    try {
        const res = await fetch(`/api/ai-edit/${currentEditId}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                section_name: sectionName,
                content: origVal,
                instruction: instr
            })
        });
        const json = await res.json();
        if(json.success) {
            contentEl.value = json.edited_content;
        } else {
            alert("AI Error: " + json.error);
            contentEl.value = origVal;
        }
    } catch(e) {
        alert("AI Request Failed");
        contentEl.value = origVal;
    }
}

window.regenerateImageFromPrompt = function() {
    const newPrompt = document.getElementById('edit-image-prompt').value;
    if(!newPrompt) return;
    
    const htmlEl = document.getElementById('edit-html-body');
    let html = htmlEl.value;
    
    // Use regex to replace the pollinations URL
    const safePrompt = encodeURIComponent(newPrompt);
    const newUrl = `https://image.pollinations.ai/prompt/${safePrompt}?width=1200&height=675&nologo=true`;
    
    const updatedHtml = html.replace(/https:\/\/image\.pollinations\.ai\/prompt\/[^"'\s>]+/, newUrl);
    htmlEl.value = updatedHtml;
    alert("Image URL updated in HTML! Click 'Save Changes' to apply.");
}

window.generateSocialFromModal = async function() {
    if(!currentEditId) return;
    document.getElementById('social-modal').classList.remove('hidden');
    const ta = document.getElementById('social-post-content');
    ta.value = "[ GENERATING_OAUTH_PAYLOAD via GROQ... ]\n\nWait 5-10 seconds for AI synthesis.";
    
    try {
        const res = await fetch(`/api/social/${currentEditId}`);
        const json = await res.json();
        if(json.success) {
            ta.value = json.post;
        } else {
            ta.value = "Error: " + json.error;
        }
    } catch(e) {
        ta.value = "Critical AI failure.";
    }
}

window.closeSocialModal = function() {
    document.getElementById('social-modal').classList.add('hidden');
}

window.copySocialPost = function() {
    const el = document.getElementById('social-post-content');
    el.select();
    document.execCommand('copy');
    alert("Social media draft copied to clipboard!");
}
