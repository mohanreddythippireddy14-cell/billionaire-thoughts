# notifier.py
# ============================================================
# Sends two types of emails:
#   1. Error alert   — when the pipeline fails, with exact fix steps
#   2. Weekly report — every Sunday with views, subs, and upload count
#
# Uses Gmail SMTP + App Password (completely free, no extra service)
# Setup: see SETUP_GUIDE.md → Step 5
# ============================================================

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import ALERT_EMAIL, EMAIL_APP_PASSWORD, EMAIL_SENDER

log = logging.getLogger("Notifier")


def _send(subject: str, html_body: str) -> bool:
    """Core email sending function. Returns True on success."""
    if not EMAIL_APP_PASSWORD:
        log.warning(
            "EMAIL_APP_PASSWORD not set — email skipped.\n"
            "Add EMAIL_APP_PASSWORD to GitHub Secrets to enable email alerts."
        )
        return False
    try:
        msg              = MIMEMultipart("alternative")
        msg["Subject"]   = subject
        msg["From"]      = EMAIL_SENDER
        msg["To"]        = ALERT_EMAIL
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_APP_PASSWORD)
            server.sendmail(EMAIL_SENDER, ALERT_EMAIL, msg.as_string())

        log.info(f"Email sent: {subject}")
        return True
    except Exception as exc:
        log.error(f"Email failed: {exc}")
        return False


# ── Error alert ───────────────────────────────────────────────

def send_error_alert(error: Exception, step: str, content_data: dict = None):
    """
    Send error email with:
    - What went wrong
    - Exactly which step failed
    - Step-by-step instructions to fix it manually
    """
    error_msg  = str(error)
    fix_steps  = _fix_steps(error_msg, step)
    title_info = ""
    if content_data:
        title_info = f"<p><strong>Content being processed:</strong> {str(content_data.get('title','N/A'))[:120]}</p>"

    html = f"""
<!DOCTYPE html>
<html><body style="font-family:Arial,sans-serif;max-width:620px;margin:0 auto;color:#222;">

<h2 style="color:#cc0000;border-bottom:2px solid #cc0000;padding-bottom:8px;">
  🚨 Pipeline Failed — {step}
</h2>

<p>Your BillionAire's_Thoughts pipeline failed at step: <strong>{step}</strong></p>

<div style="background:#fff3f3;border-left:4px solid #cc0000;padding:14px;margin:16px 0;border-radius:4px;">
  <strong>Error:</strong><br>
  <code style="color:#aa0000;word-break:break-all;">{error_msg[:600]}</code>
</div>

{title_info}

<h3 style="color:#333;">🔧 How to fix this — step by step:</h3>
<div style="background:#f0f7ff;border-left:4px solid #0066cc;padding:14px;border-radius:4px;">
  {fix_steps}
</div>

<h3>📋 Quick actions:</h3>
<ul>
  <li>Go to your GitHub repo → <strong>Actions</strong> tab → click the failed run for full logs</li>
  <li>Fix the issue using the steps above</li>
  <li>Click <strong>Re-run jobs</strong> to retry without waiting for the next schedule</li>
</ul>

<hr style="margin:24px 0;border:none;border-top:1px solid #ddd;">
<p style="color:#999;font-size:12px;">
  Automated alert from BillionAire's_Thoughts 😎<br>
  This email was sent because a pipeline run failed.
</p>
</body></html>
"""
    _send(f"🚨 Pipeline Failed — {step}", html)


def _fix_steps(error: str, step: str) -> str:
    """Return specific HTML fix instructions based on the error."""
    e = error.lower()
    s = step.lower()

    if "groq_api_key" in e or "groq" in s:
        return """
<ol>
  <li>Go to <a href="https://console.groq.com/keys">console.groq.com/keys</a></li>
  <li>Copy your API key (or create a new one if expired)</li>
  <li>Go to your GitHub repo → <strong>Settings → Secrets and variables → Actions</strong></li>
  <li>Find <strong>GROQ_API_KEY</strong> and click <em>Update</em></li>
  <li>Paste the new key and save</li>
  <li>Go to Actions tab → Re-run the failed workflow</li>
</ol>"""

    if "youtube" in s or "token" in e or "credentials" in e or "auth" in e or "401" in e or "403" in e:
        return """
<ol>
  <li>Your YouTube OAuth token has been revoked by Google (this happens rarely)</li>
  <li>On your <strong>Windows PC</strong>, open a terminal and run:<br>
      <code>python setup_auth.py</code></li>
  <li>A browser will open — log in with your YouTube channel's Google account</li>
  <li>After login, your terminal will show a long base64 string — <strong>copy it all</strong></li>
  <li>Go to GitHub repo → <strong>Settings → Secrets → YOUTUBE_TOKEN_JSON</strong></li>
  <li>Click <em>Update</em>, paste the base64 string, save</li>
  <li>Go to Actions tab → Re-run the failed workflow</li>
</ol>"""

    if "ffmpeg" in e:
        return """
<ol>
  <li>FFmpeg is missing from the GitHub Actions runner</li>
  <li>Open <strong>.github/workflows/upload.yml</strong> in your repo</li>
  <li>Make sure this exact line is in the steps section:<br>
      <code>- run: sudo apt-get install -y ffmpeg</code></li>
  <li>Commit and push the file — the next run will install FFmpeg automatically</li>
</ol>"""

    if "music" in e or "no music" in e or "mp3" in e:
        return """
<ol>
  <li>No music files found in the <strong>music/</strong> folder</li>
  <li>On your Windows PC, run: <code>python setup_music.py</code></li>
  <li>This downloads 5 free trap beats into the music/ folder</li>
  <li>Then commit them to GitHub:<br>
      <code>git add music/</code><br>
      <code>git commit -m "Add music"</code><br>
      <code>git push</code></li>
  <li>Go to Actions tab → Re-run the failed workflow</li>
</ol>"""

    if "instagram" in s:
        return """
<ol>
  <li>Your Instagram access token may have expired (they last 60 days)</li>
  <li>Go to <a href="https://developers.facebook.com/tools/explorer">developers.facebook.com/tools/explorer</a></li>
  <li>Generate a new long-lived token with <em>instagram_content_publish</em> permission</li>
  <li>Update <strong>INSTAGRAM_ACCESS_TOKEN</strong> in GitHub Secrets</li>
  <li><em>Note:</em> Instagram failure does NOT stop the YouTube upload — it still uploaded fine</li>
</ol>"""

    if "facebook" in s:
        return """
<ol>
  <li>Your Facebook Page access token may have expired (they last 60 days)</li>
  <li>Go to <a href="https://developers.facebook.com/tools/explorer">developers.facebook.com/tools/explorer</a></li>
  <li>Generate a new long-lived Page Access Token</li>
  <li>Update <strong>FACEBOOK_ACCESS_TOKEN</strong> in GitHub Secrets</li>
  <li><em>Note:</em> Facebook failure does NOT stop the YouTube upload</li>
</ol>"""

    # Generic fallback
    return f"""
<ol>
  <li>Go to your GitHub repo → <strong>Actions</strong> tab</li>
  <li>Click the failed run to see full logs</li>
  <li>Look for lines starting with <em>ERROR</em> or <em>Error</em></li>
  <li>The error message is: <code>{error[:300]}</code></li>
  <li>If you can't figure it out, screenshot the error and ask for help</li>
  <li>You can manually re-run from the Actions tab once fixed</li>
</ol>"""


# ── Weekly report ─────────────────────────────────────────────

def send_weekly_report(stats: dict):
    """Send weekly summary email every Sunday."""
    html = f"""
<!DOCTYPE html>
<html><body style="font-family:Arial,sans-serif;max-width:620px;margin:0 auto;color:#222;">

<h2 style="color:#FFD700;border-bottom:2px solid #FFD700;padding-bottom:8px;">
  📊 Weekly Report — BillionAire's_Thoughts 😎
</h2>
<p style="color:#666;">Week ending {stats.get('week_end','N/A')}</p>

<table style="width:100%;border-collapse:collapse;margin:16px 0;">
  <tr style="background:#FFD700;color:#000;">
    <th style="padding:10px;text-align:left;border-radius:4px 0 0 0;">Metric</th>
    <th style="padding:10px;text-align:right;border-radius:0 4px 0 0;">This Week</th>
  </tr>
  <tr style="background:#fafafa;">
    <td style="padding:10px;border-bottom:1px solid #eee;">📹 Videos Uploaded</td>
    <td style="padding:10px;text-align:right;border-bottom:1px solid #eee;">
      <strong>{stats.get('videos_uploaded', 0)}</strong>
    </td>
  </tr>
  <tr>
    <td style="padding:10px;border-bottom:1px solid #eee;">👁️ Total Views</td>
    <td style="padding:10px;text-align:right;border-bottom:1px solid #eee;">
      <strong>{stats.get('total_views','Check YouTube Studio')}</strong>
    </td>
  </tr>
  <tr style="background:#fafafa;">
    <td style="padding:10px;border-bottom:1px solid #eee;">👥 Subscribers Gained</td>
    <td style="padding:10px;text-align:right;border-bottom:1px solid #eee;">
      <strong>{stats.get('subscribers_gained','Check YouTube Studio')}</strong>
    </td>
  </tr>
  <tr>
    <td style="padding:10px;border-bottom:1px solid #eee;">⏱️ Watch Time (hours)</td>
    <td style="padding:10px;text-align:right;border-bottom:1px solid #eee;">
      <strong>{stats.get('watch_time_hours','Check YouTube Studio')}</strong>
    </td>
  </tr>
  <tr style="background:#fafafa;">
    <td style="padding:10px;">❌ Pipeline Failures</td>
    <td style="padding:10px;text-align:right;">
      <strong>{stats.get('failures', 0)}</strong>
    </td>
  </tr>
</table>

<div style="background:#fff8e1;border-left:4px solid #FFD700;padding:14px;border-radius:4px;margin:16px 0;">
  <strong>💡 Recommendation:</strong><br>
  {stats.get('recommendation','Keep uploading consistently — 1K subs takes ~30 days of consistency.')}
</div>

<p style="color:#888;font-size:13px;">
  Your channel is on a path to 1K subscribers 💪<br>
  Detailed analytics: <a href="https://studio.youtube.com">YouTube Studio</a>
</p>

<hr style="border:none;border-top:1px solid #eee;margin:24px 0;">
<p style="color:#bbb;font-size:11px;">
  Automated weekly report from your BillionAire's_Thoughts pipeline.
</p>
</body></html>
"""
    _send("📊 Weekly Report — BillionAire's_Thoughts 😎", html)
