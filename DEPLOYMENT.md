# Zapway Newsroom: continuous deployment

Zapway runs a dashboard plus long-running scraping and editorial workers. Deploy it as one
always-on Docker service with persistent storage. A static host such as Netlify cannot run
these workers.

## Security before publishing

Rotate the Groq key and Google app password that were previously committed in this project,
then remove them from every Git commit before pushing a public repository. Store real values
only in the host's encrypted environment-variable settings.

## Deploy with Render

The repository includes `render.yaml`. Push the reviewed code to a private GitHub repository,
then create a Render Blueprint from that repository. Render will read the Docker configuration,
create the service, mount the persistent disk at `/app/db`, and prompt for the secret values.

Use an always-on paid instance. A sleeping/free instance cannot operate the newsroom 24/7;
requests from uptime monitors do not make its worker process dependable.

Set these encrypted environment variables in Render:

| Key | Value |
| --- | --- |
| `GROQ_API_KEY` | Your rotated Groq API key |
| `ALERT_EMAIL` | Your sender address |
| `ALERT_EMAIL_APP_PASSWORD` | Your rotated Google app password |
| `WP_API_URL` | Optional WordPress API URL |
| `WP_USERNAME` | Optional WordPress account |
| `WP_APP_PASSWORD` | Optional WordPress application password |

The blueprint supplies `PORT`, `ZAPWAY_AUTO_START_WORKERS`, and the SQLite `DATABASE_URL`.
Do not supply a PostgreSQL URL: the current data layer uses SQLite directly.

## Verify

When the service becomes healthy, open its public URL and check:

- `/api/analytics`
- `/api/v1/diagnostics/ingestion-status`

The dashboard request never starts scraping. Ingestion runs continuously in the service worker
process, and the SQLite database persists on the mounted disk.
