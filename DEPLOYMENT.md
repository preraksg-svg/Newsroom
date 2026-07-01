# Zapway Newsroom — 24/7 Free Deployment Guide

This guide details how to host your Zapway Newsroom system 24/7 on the **Render Free Tier** using the pre-configured multi-stage [Dockerfile](file:///C:/Users/PIT/.gemini/antigravity/scratch/ZapwayNewsroom/Dockerfile).

---

## Step 1: Create a GitHub Repository and Push Code
Render deploys directly from GitHub. You need to push your local code there first.

1. Create a new **private** or public repository on GitHub (e.g. `zapway-newsroom`).
2. Open a terminal in `C:\Users\PIT\.gemini\antigravity\scratch\ZapwayNewsroom` and run:
   ```bash
   git init
   git add .
   git commit -m "initial commit: dockerized and ready for render deployment"
   git branch -M main
   git remote add origin <YOUR_GITHUB_REPO_URL>
   git push -u origin main
   ```

---

## Step 2: Deploy to Render (Web Service)
1. Go to [Render](https://render.com/) and sign up for a free account.
2. Click **New +** > **Web Service**.
3. Connect your GitHub account and select your `zapway-newsroom` repository.
4. Configure the service settings:
   * **Name**: `zapway-newsroom`
   * **Region**: Select the closest region to you.
   * **Branch**: `main`
   * **Runtime**: `Docker` (Render automatically detects the `Dockerfile` we created).
   * **Instance Type**: `Free` ($0/month).

---

## Step 3: Add Environment Variables
Click **Advanced** > **Add Environment Variable** in Render and enter the following settings:

| Key | Value | Description |
| :--- | :--- | :--- |
| `PORT` | `8000` | Port for the API server |
| `ZAPWAY_AUTO_START_WORKERS` | `true` | Starts the scraper/AI workers inside the web instance |
| `GROQ_API_KEY` | `gsk_3F4...` | Your Groq API key |
| `ALERT_EMAIL` | `prerakgandhi1404@gmail.com` | Email sender ID |
| `ALERT_EMAIL_APP_PASSWORD` | `uqlqawqaxmtdhgxm` | Google App password |

---

## Step 4: Configure Database Storage (Avoid Data Loss)
By default, Render's free containers are ephemeral. When the service restarts or builds, the local SQLite database (`newsroom.db`) will reset, losing your articles. 

Choose **one** of the two free solutions below to keep your data safe:

### Option A: Mount a Free Render Disk (easiest)
1. In your Render Web Service dashboard, go to **Disks** on the left menu.
2. Click **Add Disk**:
   * **Name**: `db-storage`
   * **Mount Path**: `/app/db`
   * **Size**: `1 GB` (Plenty for your database).
3. In your Render Environment Variables (Step 3), add:
   * `DATABASE_URL=sqlite:////app/db/newsroom.db`

### Option B: Use Supabase Free PostgreSQL (recommended for scale)
1. Create a free account on [Supabase](https://supabase.com/).
2. Create a new project and copy your **PostgreSQL Connection String** (URI format starting with `postgresql://...`).
3. Add it to Render Environment Variables:
   * `DATABASE_URL=<YOUR_SUPABASE_URI>`

---

## Step 5: Keep the Server Awake 24/7 (Free Keep-Alive)
Render free services go to sleep if they receive no web traffic for 15 minutes. To keep it awake and scraping 24/7:

1. Copy your deployed Render service URL (e.g., `https://zapway-newsroom.onrender.com`).
2. Go to [Cron-Job.org](https://cron-job.org/) or [UptimeRobot](https://uptimerobot.com/) and register for a free account.
3. Create a new HTTP cron job:
   * **URL**: `https://<YOUR_RENDER_URL>/api/news`
   * **Interval**: Every **10 minutes**.
4. This keep-alive ping prevents the container from ever sleeping, keeping your background workers active 24/7.
