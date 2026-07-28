# Zapway Newsroom: Continuous Deployment with Railway.app

Zapway runs a dashboard plus long-running scraping and editorial workers. Deploy it as one always-on Docker service on Railway.app with persistent storage. Static hosts like Netlify or Vercel cannot run these background workers.

## Security before publishing

Rotate any Groq keys or email app passwords that were previously committed in development, then remove them from Git history before pushing to a public repository. Store production credentials **only** in Railway's encrypted environment variables.

## Deploy with Railway.app

1. **Push Code:** Push your reviewed code to a GitHub repository (private recommended).
2. **Create Railway Project:**
   - Log in to [Railway.app](https://railway.app).
   - Click **New Project** -> **Deploy from GitHub repo** and select your repository.
3. **Configure Persistent Disk (SQLite):**
   - In your newly created service on Railway, click on the **Settings** tab.
   - Scroll down to **Volumes** and click **Add Volume**.
   - Set the mount path to `/app/db`. This ensures your `newsroom.db` SQLite database persists across deployments and doesn't get wiped out.
4. **Set Environment Variables:**
   - Go to the **Variables** tab in Railway and add the following:

| Key | Value | Description |
| --- | --- | --- |
| `PORT` | *Automatically managed by Railway* | Do not manually set this; Railway binds the port dynamically. |
| `DATABASE_URL` | `sqlite:////app/db/newsroom.db` | Absolute path pointing to the mounted persistent disk. |
| `ZAPWAY_AUTO_START_WORKERS` | `true` | Tells the FastAPI process to launch ingestion and media workers inline. |
| `GROQ_API_KEY` | `gsk_...` | Your rotated Groq API key. |
| `ALERT_EMAIL` | `your_email@gmail.com` | Notification sender address. |
| `ALERT_EMAIL_APP_PASSWORD` | `xxxx-xxxx-xxxx-xxxx` | Rotated Google App Password for SMTP alerts. |
| `WP_API_URL` | `https://your-site.com/wp-json/wp-json/wp/v2/posts` | (Optional) WordPress API endpoint. |
| `WP_USERNAME` | `admin` | (Optional) WordPress username. |
| `WP_APP_PASSWORD` | `xxxx-xxxx-xxxx-xxxx` | (Optional) WordPress application password. |

Railway will automatically read the `Dockerfile` in the root of the project, build the multi-stage image (compiling the frontend and installing Python dependencies/Playwright browsers), and launch the unified server.

## Verify the Deployment

Once the service build is complete and the deployment becomes **Active**, click the public domain provided by Railway and check:

* Dashboard home: `https://<your-railway-domain>/news`
* Stats endpoint: `https://<your-railway-domain>/api/analytics`

The ingestion and media pipelines will run continuously in the background within the same container, persisting all curated articles and growth features on your Railway volume.
