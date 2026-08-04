# Zapway Newsroom — Free 24/7 Deployment (Render + UptimeRobot)

Zapway runs a dashboard plus always-on scraping and editorial workers in a single
Docker container. This guide deploys it on **Render's free tier** and keeps it
awake 24/7 (even when your laptop is off) using **UptimeRobot**.

## Free-tier tradeoffs (read this first)

Render's free plan is genuinely free but has limits you must design around — this
repo is already configured for them:

- **512 MB RAM.** Headless-Chromium social scrapers (Twitter/Instagram/Facebook)
  would OOM-kill the process, so they are disabled via
  `ZAPWAY_DISABLE_BROWSER_SCRAPERS=true`. News still flows from the lightweight
  API/RSS sources (NewsAPI, GNews, NewsData, YouTube, Reddit, websites, feeds).
- **No persistent disk.** The SQLite DB lives inside the container and **resets on
  every redeploy/restart**. The app auto-seeds its sources and re-ingests news on
  startup, so it rebuilds itself — but curated/published state does not survive a
  redeploy. If you need durability, upgrade to a paid plan and add a disk mounted
  at `/app/db` with `DATABASE_URL=sqlite:////app/db/newsroom.db`.
- **Sleeps after ~15 min idle.** Fixed with UptimeRobot below.

## 0. Rotate your leaked Groq key FIRST

This repo previously committed a real Groq API key in source (now removed) while
public. **That key is compromised — rotate it before deploying:**

1. Go to <https://console.groq.com/keys>, delete the old key, create a new one.
2. Never put it in code. It goes only in Render's Environment tab (step 3).

## 1. Push code to GitHub

Commit your changes and push to `https://github.com/preraksg-svg/Newsroom` (or
your fork).

## 2. Create the Render service

1. Log in to <https://render.com> (free, no credit card).
2. **New → Web Service → Build and deploy from a Git repository** → select the repo.
3. Render auto-detects `render.yaml` (a Blueprint). Accept it. It sets:
   runtime = Docker, plan = free, health check = `/api/analytics`.

## 3. Set environment variables (Render → your service → Environment)

| Key | Value |
| --- | --- |
| `GROQ_API_KEY` | your **rotated** `gsk_...` key |
| `ALERT_EMAIL` | *(optional)* notification sender address |
| `ALERT_EMAIL_APP_PASSWORD` | *(optional)* Google App Password for SMTP |
| `ALERT_RECIPIENT` | *(optional)* email address to receive alerts / article readiness notifications |
| `NEWSROOM_URL` | *(optional)* your public service URL: `https://<your-service>.onrender.com` |
| `ZAPWAY_EMAIL` | *(for publishing)* your zapway.app login email |
| `ZAPWAY_PASSWORD` | *(for publishing)* your zapway.app login password |

`ZAPWAY_AUTO_START_WORKERS`, `ZAPWAY_DISABLE_BROWSER_SCRAPERS`,
`ZAPWAY_PRIMARY_MODEL`, `ZAPWAY_MAX_SOURCES_PER_CYCLE`, and `DATABASE_URL`
are already set by `render.yaml`. **Do not set `PORT`** — Render injects it.

Click **Deploy**. First build takes several minutes (it compiles the frontend and
installs Python deps). When the service is **Live**, open its URL:

- Dashboard: `https://<your-service>.onrender.com/`
- Stats API: `https://<your-service>.onrender.com/api/analytics`

## 4. Keep it awake 24/7 with UptimeRobot (primary keep-alive)

Render free services sleep after ~15 min of no traffic. UptimeRobot pings yours to
keep it up:

1. Sign up free at <https://uptimerobot.com>.
2. **Add New Monitor**:
   - Monitor Type: **HTTP(s)**
   - Friendly Name: `Zapway Newsroom`
   - URL: `https://<your-service>.onrender.com/api/analytics`
   - Monitoring Interval: **5 minutes**
3. Create it. UptimeRobot now hits the service every 5 minutes, so it never idles
   long enough to sleep.

> Note: free-tier sleep prevention keeps the container warm, but Render free
> instances still get ~750 run-hours/month per account — one always-on service
> fits within that.

### Backup keep-alive (optional)

`.github/workflows/keep-alive.yml` also pings the service on a cron. Set the repo
variable `RENDER_URL` (Settings → Secrets and variables → Actions → Variables) to
your live URL. Treat this as a backup only — GitHub cron is often delayed and is
auto-disabled after 60 days of repo inactivity.

## 5. Verify

- `GET /api/analytics` returns JSON with `"success": true`.
- After a few minutes the ingestion/AI workers populate new articles — check the
  dashboard's News board.
