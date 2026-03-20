# pipeline.py
# ============================================================
# Runs one complete upload cycle.
# Called by GitHub Actions 3× per day (6 PM, 7 PM, 8 PM IST).
# You never need to run or touch this file manually.
#
# Steps:
#   1. Generate finance content  (Groq AI — free)
#   2. Create video              (Pillow + FFmpeg)
#   3. Upload to YouTube         (Data API v3)
#   4. Upload to Instagram       (Graph API — optional)
#   5. Upload to Facebook        (Graph API — optional)
#   6. Log result
#
# On any failure:
#   - Sends email to mohanreddythippireddy14@gmail.com
#   - Includes exact fix steps
#   - Exits with code 1 (GitHub Actions marks the run as failed)
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
log = logging.getLogger("Pipeline")


def _log_upload(video_id: str, content_data: dict, platforms: dict):
    """Append successful upload to .logs/uploads.json (kept forever)."""
    from config import LOGS_DIR
    f = LOGS_DIR / "uploads.json"
    try:
        existing = json.loads(f.read_text(encoding="utf-8")) if f.exists() else []
        existing.append({
            "timestamp":  datetime.datetime.now().isoformat(),
            "youtube_id": video_id,
            "title":      content_data.get("title", ""),
            "mood":       content_data.get("mood", ""),
            "platforms":  platforms,
        })
        f.write_text(json.dumps(existing[-500:], indent=2), encoding="utf-8")
    except Exception as exc:
        log.warning(f"Could not write upload log: {exc}")


def _log_failure(step: str, error: str):
    """Append failure to .logs/failures.json."""
    from config import LOGS_DIR
    f = LOGS_DIR / "failures.json"
    try:
        existing = json.loads(f.read_text(encoding="utf-8")) if f.exists() else []
        existing.append({
            "timestamp": datetime.datetime.now().isoformat(),
            "step":      step,
            "error":     error[:500],
        })
        f.write_text(json.dumps(existing[-200:], indent=2), encoding="utf-8")
    except Exception as exc:
        log.warning(f"Could not write failure log: {exc}")


def run():
    now = datetime.datetime.now().isoformat()
    print("\n" + "═" * 60)
    print(f"  💰 PIPELINE STARTING — {now[:19]}")
    print(f"  BillionAire's_Thoughts 😎")
    print("═" * 60)

    content_data = None
    video_path   = None
    step         = "Startup"

    try:
        # ── 1. Generate finance content ───────────────────────────
        step = "Content Generation (Groq AI)"
        print(f"\n[1/5] {step}...")
        from quote_engine import generate_content
        content_data = generate_content()
        print(f"  ✓ Title:   {content_data['title']}")
        print(f"  ✓ Mood:    {content_data['mood']}")
        print(f"  ✓ Content: {content_data['content'][:90]}...")

        # ── 2. Create video ───────────────────────────────────────
        step = "Video Creation (Pillow + FFmpeg)"
        print(f"\n[2/5] {step}...")
        from video_creator import create_video
        video_path = create_video(content_data)
        size_mb = video_path.stat().st_size / 1_000_000
        print(f"  ✓ Video: {video_path.name} ({size_mb:.1f} MB)")

        # ── 3. Upload to YouTube ──────────────────────────────────
        step = "YouTube Upload"
        print(f"\n[3/5] {step}...")
        from youtube_uploader import upload_to_youtube
        youtube_id = upload_to_youtube(video_path, content_data)
        print(f"  ✓ YouTube: https://youtube.com/watch?v={youtube_id}")

        # ── 4. Upload to Instagram ────────────────────────────────
        step = "Instagram Upload"
        print(f"\n[4/5] {step}...")
        from instagram_uploader import upload_to_instagram
        ig_id = upload_to_instagram(video_path, content_data)
        print(f"  {'✓ Instagram: ' + ig_id if ig_id else '⚠ Instagram: skipped (credentials not set)'}")

        # ── 5. Upload to Facebook ─────────────────────────────────
        step = "Facebook Upload"
        print(f"\n[5/5] {step}...")
        from facebook_uploader import upload_to_facebook
        fb_id = upload_to_facebook(video_path, content_data)
        print(f"  {'✓ Facebook: ' + fb_id if fb_id else '⚠ Facebook: skipped (credentials not set)'}")

        # ── Log success ───────────────────────────────────────────
        _log_upload(youtube_id, content_data, {
            "youtube":   youtube_id,
            "instagram": ig_id,
            "facebook":  fb_id,
        })

        print("\n" + "═" * 60)
        print("  ✅ PIPELINE COMPLETE — video live on YouTube!")
        print("═" * 60 + "\n")

    except Exception as exc:
        log.error(f"Pipeline FAILED at [{step}]: {exc}", exc_info=True)
        _log_failure(step, str(exc))

        # Send error email with fix steps
        try:
            from notifier import send_error_alert
            send_error_alert(exc, step, content_data)
            print(f"  📧 Error email sent to mohanreddythippireddy14@gmail.com")
        except Exception as mail_err:
            log.warning(f"Could not send error email: {mail_err}")

        print("\n" + "═" * 60)
        print(f"  ❌ PIPELINE FAILED — {step}")
        print("═" * 60 + "\n")
        sys.exit(1)     # GitHub Actions marks run as FAILED

    finally:
        # Always clean up the temp video file
        if video_path and video_path.exists():
            try:
                video_path.unlink()
            except Exception:
                pass


if __name__ == "__main__":
    run()
