# analytics.py
# ============================================================
# Weekly Analytics + Groq Content Intelligence
#
# What this does every Sunday at 9:30 AM IST:
#   1. Pulls last 7 days of data from YouTube Analytics API
#   2. Gets per-video performance (views, watch time, likes)
#   3. Feeds all data to Groq for analysis
#   4. Groq identifies patterns — what topics/styles worked
#   5. Groq generates 10 content ideas for next week
#   6. Ideas saved to .logs/next_week_ideas.json
#   7. pipeline.py uses those ideas automatically next week
#   8. Full report emailed to mohanreddythippireddy14@gmail.com
#
# Run manually: python analytics.py
# ============================================================

import datetime
import json
import logging
import os
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("Analytics")


# ── YouTube Analytics ─────────────────────────────────────────

def _get_credentials():
    """Get authenticated Google credentials from saved token."""
    from config import YOUTUBE_TOKEN_FILE
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    if not YOUTUBE_TOKEN_FILE.exists():
        raise FileNotFoundError(
            "youtube_token.json not found.\n"
            "Run setup_auth.py and update YOUTUBE_TOKEN_JSON in GitHub Secrets."
        )

    raw   = json.loads(YOUTUBE_TOKEN_FILE.read_text(encoding="utf-8"))
    creds = Credentials(
        token         = raw.get("token"),
        refresh_token = raw.get("refresh_token"),
        token_uri     = raw.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id     = raw.get("client_id"),
        client_secret = raw.get("client_secret"),
        scopes        = raw.get("scopes", []),
    )
    if creds.expired and creds.refresh_token:
        log.info("Refreshing access token...")
        creds.refresh(Request())
    return creds


def _fetch_channel_stats(creds) -> dict:
    """Fetch overall channel stats for last 7 days."""
    try:
        from googleapiclient.discovery import build

        yt    = build("youtubeAnalytics", "v2", credentials=creds)
        end   = datetime.date.today()
        start = end - datetime.timedelta(days=7)

        resp = yt.reports().query(
            ids        = "channel==MINE",
            startDate  = start.isoformat(),
            endDate    = end.isoformat(),
            metrics    = "views,estimatedMinutesWatched,likes,subscribersGained,subscribersLost,averageViewDuration",
            dimensions = "day",
        ).execute()

        rows          = resp.get("rows", [])
        total_views   = sum(int(r[1])   for r in rows)
        total_minutes = sum(int(r[2])   for r in rows)
        total_likes   = sum(int(r[3])   for r in rows)
        subs_gained   = sum(int(r[4])   for r in rows)
        subs_lost     = sum(int(r[5])   for r in rows)
        avg_duration  = (sum(float(r[6]) for r in rows) / len(rows)) if rows else 0

        return {
            "total_views":     total_views,
            "watch_time_mins": total_minutes,
            "watch_time_hours": round(total_minutes / 60, 1),
            "total_likes":     total_likes,
            "subs_gained":     subs_gained,
            "subs_lost":       subs_lost,
            "net_subs":        subs_gained - subs_lost,
            "avg_view_duration_sec": round(avg_duration, 1),
            "period":          f"{start.isoformat()} to {end.isoformat()}",
        }
    except Exception as exc:
        log.warning(f"Could not fetch channel stats: {exc}")
        return {}


def _fetch_video_stats(creds) -> list:
    """Fetch per-video performance for last 7 days."""
    try:
        from googleapiclient.discovery import build

        yt    = build("youtubeAnalytics", "v2", credentials=creds)
        end   = datetime.date.today()
        start = end - datetime.timedelta(days=7)

        resp = yt.reports().query(
            ids        = "channel==MINE",
            startDate  = start.isoformat(),
            endDate    = end.isoformat(),
            metrics    = "views,estimatedMinutesWatched,likes,subscribersGained,averageViewDuration",
            dimensions = "video",
            sort       = "-views",
            maxResults = 20,
        ).execute()

        videos = []
        for row in resp.get("rows", []):
            videos.append({
                "video_id":        row[0],
                "views":           int(row[1]),
                "watch_mins":      int(row[2]),
                "likes":           int(row[3]),
                "subs_gained":     int(row[4]),
                "avg_duration_sec": round(float(row[5]), 1),
                "url":             f"https://youtube.com/shorts/{row[0]}",
            })
        return videos

    except Exception as exc:
        log.warning(f"Could not fetch video stats: {exc}")
        return []


def _enrich_with_titles(creds, videos: list) -> list:
    """Add video titles to the video stats list."""
    if not videos:
        return videos
    try:
        from googleapiclient.discovery import build

        yt  = build("youtube", "v3", credentials=creds)
        ids = [v["video_id"] for v in videos]

        # Process in batches of 50 (API limit)
        for i in range(0, len(ids), 50):
            batch = ids[i:i+50]
            resp  = yt.videos().list(
                part = "snippet",
                id   = ",".join(batch),
            ).execute()
            title_map = {
                item["id"]: item["snippet"]["title"]
                for item in resp.get("items", [])
            }
            for v in videos:
                if v["video_id"] in title_map:
                    v["title"] = title_map[v["video_id"]]

    except Exception as exc:
        log.warning(f"Could not fetch video titles: {exc}")
        for v in videos:
            if "title" not in v:
                v["title"] = v["video_id"]
    return videos


# ── Groq Analysis ─────────────────────────────────────────────

def _groq_analyse(channel_stats: dict, videos: list, upload_count: int, failures: int) -> dict:
    """
    Feed all data to Groq.
    Returns: analysis text + 10 content ideas for next week.
    """
    import httpx
    from groq import Groq
    from config import GROQ_API_KEY

    if not GROQ_API_KEY:
        log.warning("GROQ_API_KEY not set — skipping AI analysis")
        return {"analysis": "Groq API key not set.", "ideas": []}

    client = Groq(
        api_key=GROQ_API_KEY,
        http_client=httpx.Client(timeout=60.0, trust_env=False),
    )

    # Format video data for the prompt
    top_videos_text = ""
    for i, v in enumerate(videos[:10], 1):
        top_videos_text += (
            f"  {i}. \"{v.get('title', 'Unknown')}\" — "
            f"{v['views']} views, {v['subs_gained']} subs gained, "
            f"{v['likes']} likes, avg watch {v['avg_duration_sec']}s\n"
        )

    bottom_videos_text = ""
    for i, v in enumerate(videos[-5:], 1):
        bottom_videos_text += (
            f"  {i}. \"{v.get('title', 'Unknown')}\" — "
            f"{v['views']} views, {v['subs_gained']} subs gained\n"
        )

    prompt = f"""You are a YouTube growth analyst specialising in short-form motivational/mindset content.

Analyse this weekly data for the channel "BillionAire's _Thoughts" and provide actionable intelligence.

CHANNEL STATS (last 7 days):
- Total views: {channel_stats.get('total_views', 'N/A')}
- Watch time: {channel_stats.get('watch_time_hours', 'N/A')} hours
- Net subscribers gained: {channel_stats.get('net_subs', 'N/A')}
- Average view duration: {channel_stats.get('avg_view_duration_sec', 'N/A')} seconds
- Videos uploaded: {upload_count}
- Pipeline failures: {failures}

TOP PERFORMING VIDEOS:
{top_videos_text if top_videos_text else '  No data available'}

WORST PERFORMING VIDEOS:
{bottom_videos_text if bottom_videos_text else '  No data available'}

CHANNEL NICHE: Raw masculine mindset, silent strength, brutal self-improvement truths.
TARGET AUDIENCE: Men aged 16-35 globally.
VIDEO FORMAT: 27-second Shorts with bold text on dark cinematic background, trap music.

Your task:
1. Identify 2-3 specific PATTERNS in what worked (topics, angles, word choices in titles)
2. Identify 1-2 things that clearly did NOT work
3. Calculate the subscribe conversion rate (subs gained / views) and benchmark it
4. Give 3 specific, immediately actionable improvements
5. Generate exactly 10 content theme ideas for next week — these must be SPECIFIC angles, not generic. Each must be a complete sentence describing exactly what the video should say. Base them on what worked this week.

Return ONLY a valid JSON object, no markdown, no extra text:
{{
  "patterns_that_worked": ["pattern 1", "pattern 2", "pattern 3"],
  "patterns_that_failed": ["pattern 1", "pattern 2"],
  "sub_conversion_rate": "X.XX%",
  "conversion_benchmark": "above/below/at industry average of 0.5-1.5% for Shorts",
  "immediate_actions": ["action 1", "action 2", "action 3"],
  "weekly_summary": "2-3 sentence honest summary of the week",
  "next_week_ideas": [
    "complete content theme sentence 1",
    "complete content theme sentence 2",
    "complete content theme sentence 3",
    "complete content theme sentence 4",
    "complete content theme sentence 5",
    "complete content theme sentence 6",
    "complete content theme sentence 7",
    "complete content theme sentence 8",
    "complete content theme sentence 9",
    "complete content theme sentence 10"
  ]
}}"""

    try:
        resp = client.chat.completions.create(
            model       = "llama-3.1-8b-instant",
            messages    = [{"role": "user", "content": prompt}],
            temperature = 0.7,
        )
        raw  = resp.choices[0].message.content.strip()
        raw  = raw.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)
        log.info("Groq analysis complete")
        return data
    except Exception as exc:
        log.error(f"Groq analysis failed: {exc}")
        return {
            "analysis":     f"Groq analysis failed: {exc}",
            "next_week_ideas": [],
        }


# ── Save Ideas for Pipeline ───────────────────────────────────

def _save_next_week_ideas(ideas: list):
    """
    Save Groq-generated ideas to .logs/next_week_ideas.json
    pipeline.py will use these instead of static CONTENT_THEMES next week.
    """
    from config import LOGS_DIR

    if not ideas:
        log.warning("No ideas to save — pipeline will use default themes next week")
        return

    f = LOGS_DIR / "next_week_ideas.json"
    data = {
        "generated_at": datetime.datetime.now().isoformat(),
        "valid_until":  (datetime.date.today() + datetime.timedelta(days=7)).isoformat(),
        "ideas":        ideas,
    }
    f.write_text(json.dumps(data, indent=2), encoding="utf-8")
    log.info(f"Saved {len(ideas)} content ideas to {f}")


# ── Upload/Failure counters ───────────────────────────────────

def _count_uploads_this_week() -> int:
    from config import LOGS_DIR
    f = LOGS_DIR / "uploads.json"
    if not f.exists():
        return 0
    since = datetime.datetime.now() - datetime.timedelta(days=7)
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
        return sum(
            1 for u in data
            if datetime.datetime.fromisoformat(u.get("timestamp", "2000-01-01")) >= since
        )
    except Exception:
        return 0


def _count_failures_this_week() -> int:
    from config import LOGS_DIR
    f = LOGS_DIR / "failures.json"
    if not f.exists():
        return 0
    since = datetime.datetime.now() - datetime.timedelta(days=7)
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
        return sum(
            1 for u in data
            if datetime.datetime.fromisoformat(u.get("timestamp", "2000-01-01")) >= since
        )
    except Exception:
        return 0


# ── Email Report ──────────────────────────────────────────────

def _send_report(channel_stats: dict, videos: list, groq_data: dict,
                 upload_count: int, failures: int):
    """Send full weekly report email."""
    from notifier import _send

    top_videos_html = ""
    for i, v in enumerate(videos[:5], 1):
        bar_width = min(100, int(v["views"] / max(1, videos[0]["views"]) * 100))
        top_videos_html += f"""
        <tr>
          <td style="padding:8px 0;font-size:13px;color:#333;">{i}. {v.get('title', v['video_id'])[:55]}...</td>
          <td style="padding:8px 0;font-size:13px;text-align:right;white-space:nowrap;">
            {v['views']:,} views &nbsp;|&nbsp; +{v['subs_gained']} subs
          </td>
        </tr>
        <tr>
          <td colspan="2" style="padding-bottom:8px;">
            <div style="height:4px;background:#eee;border-radius:2px;">
              <div style="height:4px;background:#FFD700;border-radius:2px;width:{bar_width}%;"></div>
            </div>
          </td>
        </tr>"""

    ideas_html = ""
    for i, idea in enumerate(groq_data.get("next_week_ideas", [])[:10], 1):
        ideas_html += f'<li style="margin-bottom:6px;font-size:13px;color:#333;">{idea}</li>'

    actions_html = ""
    for action in groq_data.get("immediate_actions", []):
        actions_html += f'<li style="margin-bottom:6px;font-size:13px;color:#333;">{action}</li>'

    patterns_html = ""
    for p in groq_data.get("patterns_that_worked", []):
        patterns_html += f'<li style="margin-bottom:4px;font-size:13px;color:#1a6b3c;">{p}</li>'

    failed_html = ""
    for p in groq_data.get("patterns_that_failed", []):
        failed_html += f'<li style="margin-bottom:4px;font-size:13px;color:#cc0000;">{p}</li>'

    week_end = datetime.date.today().strftime("%B %d, %Y")

    html = f"""<!DOCTYPE html>
<html><body style="font-family:Arial,sans-serif;max-width:640px;margin:0 auto;color:#222;background:#fff;">

<div style="background:#000;padding:24px;text-align:center;border-radius:8px 8px 0 0;">
  <h1 style="color:#FFD700;margin:0;font-size:22px;">BillionAire's _Thoughts 😎</h1>
  <p style="color:#999;margin:6px 0 0;font-size:13px;">Weekly Intelligence Report — {week_end}</p>
</div>

<div style="padding:24px;">

  <table style="width:100%;border-collapse:collapse;margin-bottom:24px;">
    <tr>
      <td style="background:#f9f9f9;border-radius:8px;padding:14px;text-align:center;width:25%;">
        <div style="font-size:24px;font-weight:700;color:#000;">{channel_stats.get('total_views', 0):,}</div>
        <div style="font-size:11px;color:#888;margin-top:3px;">Total views</div>
      </td>
      <td style="width:2%;"></td>
      <td style="background:#f9f9f9;border-radius:8px;padding:14px;text-align:center;width:25%;">
        <div style="font-size:24px;font-weight:700;color:#000;">+{channel_stats.get('net_subs', 0)}</div>
        <div style="font-size:11px;color:#888;margin-top:3px;">Net subscribers</div>
      </td>
      <td style="width:2%;"></td>
      <td style="background:#f9f9f9;border-radius:8px;padding:14px;text-align:center;width:25%;">
        <div style="font-size:24px;font-weight:700;color:#000;">{channel_stats.get('watch_time_hours', 0)}h</div>
        <div style="font-size:11px;color:#888;margin-top:3px;">Watch time</div>
      </td>
      <td style="width:2%;"></td>
      <td style="background:#f9f9f9;border-radius:8px;padding:14px;text-align:center;width:25%;">
        <div style="font-size:24px;font-weight:700;color:#000;">{upload_count}</div>
        <div style="font-size:11px;color:#888;margin-top:3px;">Videos uploaded</div>
      </td>
    </tr>
  </table>

  <div style="background:#fff8e1;border-left:4px solid #FFD700;padding:14px;border-radius:0 8px 8px 0;margin-bottom:20px;">
    <strong style="font-size:14px;">AI Summary</strong>
    <p style="margin:8px 0 0;font-size:13px;color:#555;line-height:1.6;">
      {groq_data.get('weekly_summary', 'Analysis not available.')}
    </p>
  </div>

  <div style="background:#fff8e1;border:1px solid #FFD700;border-radius:8px;padding:14px;margin-bottom:20px;">
    <strong style="font-size:13px;">Subscribe conversion rate: {groq_data.get('sub_conversion_rate', 'N/A')}</strong><br>
    <span style="font-size:12px;color:#888;">{groq_data.get('conversion_benchmark', '')}</span>
  </div>

  <h3 style="font-size:15px;margin-bottom:12px;border-bottom:2px solid #FFD700;padding-bottom:6px;">
    Top performing videos this week
  </h3>
  <table style="width:100%;">{top_videos_html}</table>

  <h3 style="font-size:15px;margin:20px 0 10px;border-bottom:2px solid #4CAF50;padding-bottom:6px;">
    What worked
  </h3>
  <ul style="margin:0;padding-left:18px;">{patterns_html}</ul>

  <h3 style="font-size:15px;margin:20px 0 10px;border-bottom:2px solid #cc0000;padding-bottom:6px;">
    What did NOT work
  </h3>
  <ul style="margin:0;padding-left:18px;">{failed_html}</ul>

  <h3 style="font-size:15px;margin:20px 0 10px;border-bottom:2px solid #2196F3;padding-bottom:6px;">
    3 things to do this week
  </h3>
  <ul style="margin:0;padding-left:18px;">{actions_html}</ul>

  <h3 style="font-size:15px;margin:20px 0 10px;border-bottom:2px solid #9C27B0;padding-bottom:6px;">
    Next week's content ideas (auto-loaded into pipeline)
  </h3>
  <ol style="margin:0;padding-left:18px;">{ideas_html}</ol>
  <p style="font-size:11px;color:#888;margin-top:8px;">
    These 10 ideas have been automatically saved. Your pipeline will use them next week instead of the default themes.
  </p>

  {"<div style='background:#fff3f3;border:1px solid #cc0000;border-radius:8px;padding:12px;margin-top:20px;'><strong style='color:#cc0000;font-size:13px;'>Pipeline issues this week: " + str(failures) + " failures</strong><br><span style='font-size:12px;color:#888;'>Check GitHub Actions → look for red runs → fix errors shown in the logs.</span></div>" if failures > 0 else ""}

</div>

<div style="background:#f5f5f5;padding:16px;text-align:center;border-radius:0 0 8px 8px;">
  <p style="font-size:11px;color:#aaa;margin:0;">
    Automated weekly report — BillionAire's_Thoughts 😎<br>
    Check YouTube Studio for full analytics: studio.youtube.com
  </p>
</div>

</body></html>"""

    subject = f"📊 Weekly Report — {channel_stats.get('net_subs', 0):+d} subs | {channel_stats.get('total_views', 0):,} views | {week_end}"
    _send(subject, html)


# ── Main ──────────────────────────────────────────────────────

def run_weekly_report():
    log.info("=" * 55)
    log.info("  Weekly Analytics — BillionAire's_Thoughts")
    log.info("=" * 55)

    # 1. Get credentials
    log.info("Authenticating with YouTube...")
    try:
        creds = _get_credentials()
    except Exception as exc:
        log.error(f"Auth failed: {exc}")
        sys.exit(1)

    # 2. Fetch data
    log.info("Fetching channel stats...")
    channel_stats = _fetch_channel_stats(creds)
    log.info(f"  Views: {channel_stats.get('total_views', 0):,}")
    log.info(f"  Net subs: {channel_stats.get('net_subs', 0):+d}")

    log.info("Fetching per-video performance...")
    videos = _fetch_video_stats(creds)
    videos = _enrich_with_titles(creds, videos)
    log.info(f"  {len(videos)} videos found")

    # 3. Local counts
    upload_count = _count_uploads_this_week()
    failures     = _count_failures_this_week()
    log.info(f"  Pipeline: {upload_count} uploads, {failures} failures")

    # 4. Groq analysis
    log.info("Running Groq analysis...")
    groq_data = _groq_analyse(channel_stats, videos, upload_count, failures)

    # 5. Save next week's ideas for pipeline
    _save_next_week_ideas(groq_data.get("next_week_ideas", []))

    # 6. Send email
    log.info("Sending weekly report email...")
    _send_report(channel_stats, videos, groq_data, upload_count, failures)

    log.info("=" * 55)
    log.info("  Weekly report complete!")
    log.info(f"  Email sent to mohanreddythippireddy14@gmail.com")
    log.info("=" * 55)


if __name__ == "__main__":
    run_weekly_report()
