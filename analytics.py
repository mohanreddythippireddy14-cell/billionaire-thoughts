# analytics.py
# ============================================================
# Generates and sends the weekly performance email
# Runs every Sunday at 9:30 AM IST via GitHub Actions
# ============================================================

import datetime
import json
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("Analytics")


def _count_uploads(since: datetime.datetime) -> int:
    from config import LOGS_DIR
    f = LOGS_DIR / "uploads.json"
    if not f.exists():
        return 0
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
        return sum(
            1 for u in data
            if datetime.datetime.fromisoformat(u.get("timestamp", "2000-01-01")) >= since
        )
    except Exception:
        return 0


def _count_failures(since: datetime.datetime) -> int:
    from config import LOGS_DIR
    f = LOGS_DIR / "failures.json"
    if not f.exists():
        return 0
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
        return sum(
            1 for u in data
            if datetime.datetime.fromisoformat(u.get("timestamp", "2000-01-01")) >= since
        )
    except Exception:
        return 0


def _youtube_stats() -> dict:
    """Fetch real stats from YouTube Analytics API."""
    try:
        import json
        from config import YOUTUBE_TOKEN_FILE
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        raw   = json.loads(YOUTUBE_TOKEN_FILE.read_text())
        creds = Credentials(
            token         = raw.get("token"),
            refresh_token = raw.get("refresh_token"),
            token_uri     = raw.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id     = raw.get("client_id"),
            client_secret = raw.get("client_secret"),
            scopes        = [
                "https://www.googleapis.com/auth/youtube.readonly",
                "https://www.googleapis.com/auth/yt-analytics.readonly",
            ],
        )
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())

        yt   = build("youtubeAnalytics", "v2", credentials=creds)
        end  = datetime.date.today()
        start = end - datetime.timedelta(days=7)

        resp = yt.reports().query(
            ids      = "channel==MINE",
            startDate = start.isoformat(),
            endDate   = end.isoformat(),
            metrics   = "views,estimatedMinutesWatched,subscribersGained",
            dimensions= "day",
        ).execute()

        rows  = resp.get("rows", [])
        views = sum(int(r[1]) for r in rows)
        mins  = sum(int(r[2]) for r in rows)
        subs  = sum(int(r[3]) for r in rows)

        return {
            "total_views":        f"{views:,}",
            "watch_time_hours":   f"{mins // 60:,}",
            "subscribers_gained": f"+{subs}",
        }

    except Exception as exc:
        log.warning(f"Could not fetch YouTube Analytics: {exc}")
        return {
            "total_views":        "Open YouTube Studio to check",
            "watch_time_hours":   "Open YouTube Studio to check",
            "subscribers_gained": "Open YouTube Studio to check",
        }


def _recommendation(uploads: int, failures: int) -> str:
    if failures > uploads * 0.5:
        return (
            "⚠️ More than half of your runs failed this week. "
            "Check GitHub Actions logs and fix the errors — "
            "the pipeline is not running reliably."
        )
    target = 21   # 3 videos/day × 7 days
    if uploads < target * 0.7:
        return (
            f"📉 Only {uploads} videos uploaded this week (target: {target}). "
            "Check if the GitHub Actions cron job is running. "
            "Go to Actions tab and look for failed or missing runs."
        )
    return (
        f"✅ Great week — {uploads} videos uploaded. "
        "Stay consistent. At this rate you'll hit 1K subscribers "
        "in about {days} days.".format(days=max(7, 30 - uploads // 2))
    )


def run_weekly_report():
    from notifier import send_weekly_report

    log.info("Generating weekly report...")
    since    = datetime.datetime.now() - datetime.timedelta(days=7)
    uploads  = _count_uploads(since)
    failures = _count_failures(since)
    yt_stats = _youtube_stats()

    stats = {
        "week_end":       datetime.date.today().strftime("%B %d, %Y"),
        "videos_uploaded": uploads,
        "failures":        failures,
        "recommendation":  _recommendation(uploads, failures),
        **yt_stats,
    }

    send_weekly_report(stats)
    log.info("Weekly report sent to mohanreddythippireddy14@gmail.com")


if __name__ == "__main__":
    run_weekly_report()
