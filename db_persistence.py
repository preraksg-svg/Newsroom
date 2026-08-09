"""
Free, no-credit-card persistence for the SQLite DB on hosts without a disk
(e.g. Render free tier). The DB is snapshotted (gzip) to a GitHub Release asset:
restored on startup, backed up periodically and on shutdown. Keeps plain SQLite
everywhere else, so it is a drop-in with zero query changes.

Enable by setting these env vars (all optional — absent = current ephemeral mode):
  GITHUB_TOKEN   : a token with 'contents: write' on the repo (fine-grained ok)
  GITHUB_REPO    : "owner/name" (defaults to preraksg-svg/Newsroom)
  DB_BACKUP_TAG  : release tag to store the snapshot (default "db-backup")
  DB_BACKUP_INTERVAL_MIN : minutes between backups (default 30)
"""
import os
import gzip
import asyncio

try:
    from backend.db.queries import DB_PATH
except Exception:
    DB_PATH = os.path.join(os.path.dirname(__file__), "newsroom.db")

_TOKEN = os.getenv("GITHUB_TOKEN")
_REPO = os.getenv("GITHUB_REPO", "preraksg-svg/Newsroom")
_TAG = os.getenv("DB_BACKUP_TAG", "db-backup")
_ASSET = "newsroom.db.gz"
_API = "https://api.github.com"


def enabled():
    return bool(_TOKEN)


def _headers():
    return {"Authorization": f"Bearer {_TOKEN}", "Accept": "application/vnd.github+json"}


def _get_or_create_release():
    import requests
    r = requests.get(f"{_API}/repos/{_REPO}/releases/tags/{_TAG}", headers=_headers(), timeout=20)
    if r.status_code == 200:
        return r.json()
    r = requests.post(
        f"{_API}/repos/{_REPO}/releases", headers=_headers(),
        json={"tag_name": _TAG, "name": "DB Backup (automated)",
              "body": "Automated Zapway DB snapshot. Do not delete.", "prerelease": True},
        timeout=20,
    )
    if r.status_code in (200, 201):
        return r.json()
    print(f"[DB-PERSIST] Could not get/create release: {r.status_code} {r.text[:120]}")
    return None


def restore_db():
    """Download the latest DB snapshot into DB_PATH. Call BEFORE init_db()."""
    if not _TOKEN:
        return False
    try:
        import requests
        rel = _get_or_create_release()
        if not rel:
            return False
        asset = next((a for a in rel.get("assets", []) if a["name"] == _ASSET), None)
        if not asset:
            print("[DB-PERSIST] No existing backup yet (fresh start).")
            return False
        dl = requests.get(
            f"{_API}/repos/{_REPO}/releases/assets/{asset['id']}",
            headers={"Authorization": f"Bearer {_TOKEN}", "Accept": "application/octet-stream"},
            timeout=90,
        )
        if dl.status_code != 200:
            print(f"[DB-PERSIST] Restore download failed: {dl.status_code}")
            return False
        data = gzip.decompress(dl.content)
        os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
        with open(DB_PATH, "wb") as f:
            f.write(data)
        print(f"[DB-PERSIST] Restored DB from GitHub backup ({len(data)} bytes).")
        return True
    except Exception as e:
        print(f"[DB-PERSIST] Restore failed (continuing with local DB): {e}")
        return False


def backup_db():
    """Gzip DB_PATH and upload it as the release asset (overwrites previous)."""
    if not _TOKEN:
        return False
    try:
        import requests
        if not os.path.exists(DB_PATH):
            return False
        with open(DB_PATH, "rb") as f:
            gz = gzip.compress(f.read())
        rel = _get_or_create_release()
        if not rel:
            return False
        for a in rel.get("assets", []):
            if a["name"] == _ASSET:
                requests.delete(f"{_API}/repos/{_REPO}/releases/assets/{a['id']}", headers=_headers(), timeout=20)
        upload_url = rel["upload_url"].split("{")[0]
        up = requests.post(
            f"{upload_url}?name={_ASSET}",
            headers={"Authorization": f"Bearer {_TOKEN}", "Content-Type": "application/gzip"},
            data=gz, timeout=180,
        )
        if up.status_code in (200, 201):
            print(f"[DB-PERSIST] Backed up DB to GitHub ({len(gz)} bytes gz).")
            return True
        print(f"[DB-PERSIST] Backup upload failed: {up.status_code} {up.text[:120]}")
        return False
    except Exception as e:
        print(f"[DB-PERSIST] Backup failed: {e}")
        return False


async def backup_loop():
    """Background task: periodically snapshot the DB to GitHub."""
    if not _TOKEN:
        return
    try:
        interval = max(5, int(os.getenv("DB_BACKUP_INTERVAL_MIN", "30")))
    except ValueError:
        interval = 30
    while True:
        await asyncio.sleep(interval * 60)
        await asyncio.to_thread(backup_db)
