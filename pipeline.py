# pipeline.py
# ============================================================
# Runs one complete upload cycle.
# Called by GitHub Actions 3x per day — each with a different
# TARGET_AUDIENCE env variable (us / europe / asia).
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
log = logging.getLogger("Pipeline")

TARGET_AUDIENCE = os.environ.get("TARGET_AUDIENCE", "us")


def _log_upload(video_id: str, content_data: dict, platforms: dict):
    from config import LOGS_DIR
    f = LOGS_DIR / "uploads.json"
    try:
        existing = json.loads(f.read_text(encoding="utf-8")) if f.exists() else []
        existing.append({
            "timestamp":  datetime.datetime.now().isoformat(),
            "youtube_id": video_id,
            "title":      content_data.get("title", ""),
            "mood":       content_data.get("mood", ""),
            "audience":   content_data.get("audience", TARGET_AUDIENCE),
            "hook":       content_data.get("hook", "")[:80],
            "platforms":  platforms,
        })
        f.write_text(json.dumps(existing[-500:], indent=2), encoding="utf-8")
    except Exception as exc:
        log.warning(f"Could not write upload log: {exc}")


def _log_failure(step: str, error: str):
    from config import LOGS_DIR
    f = LOGS_DIR / "failures.json"
    try:
        existing = json.loads(f.read_text(encoding="utf-8")) if f.exists() else []
        existing.append({
            "timestamp": datetime.datetime.now().isoformat(),
            "step":      step,
            "audience":  TARGET_AUDIENCE,
            "error":     error[:500],
        })
        f.write_text(json.dumps(existing[-200:], indent=2), encoding="utf-8")
    except Exception as exc:
        log.warning(f"Could not write failure log: {exc}")


def run():
    now = datetime.datetime.now().isoformat()
    audience_labels = {
        "us":     "US      🇺🇸  8PM EST",
        "europe": "Europe  🇪🇺  9PM CET",
        "asia":   "Asia    🌏  9PM IST",
    }
    label = audience_labels.get(TARGET_AUDIENCE, TARGET_AUDIENCE)

    print("\n" + "═" * 60)
    print(f"  💰 PIPELINE STARTING — {now[:19]}")
    print(f"  BillionAire's_Thoughts 😎")
    print(f"  Target audience: {label}")
    print("═" * 60)

    content_data = None
    video_path   = None
    step         = "Startup"

    try:
        # 1. Generate content
        step = "Content Generation (Groq AI)"
        print(f"\n[1/5] {step}...")
        from quote_engine import generate_content
        content_data = generate_content()
        print(f"  ✓ Audience: {content_data.get('audience', TARGET_AUDIENCE)}")
        print(f"  ✓ Mood:     {content_data['mood']}")
        print(f"  ✓ Hook:     {content_data['hook'][:80]}...")
        print(f"  ✓ Answer:   {content_data['answer'][:80]}...")
        print(f"  ✓ Title:    {content_data['title']}")

        # 2. Create video
        step = "Video Creation (Pexels + FFmpeg)"
        print(f"\n[2/5] {step}...")
        from video_creator import create_video
        video_path = create_video(content_data)
        size_mb = video_path.stat().st_size / 1_000_000
        print(f"  ✓ Video: {video_path.name} ({size_mb:.1f} MB)")

        # 3. Upload to YouTube
        step = "YouTube Upload"
        print(f"\n[3/5] {step}...")
        from youtube_uploader import upload_to_youtube
        youtube_id = upload_to_youtube(video_path, content_data)
        print(f"  ✓ YouTube: https://youtube.com/shorts/{youtube_id}")

        # 4. Instagram
        step = "Instagram Upload"
        print(f"\n[4/5] {step}...")
        from instagram_uploader import upload_to_instagram
        ig_id = upload_to_instagram(video_path, content_data)
        print(f"  {'✓ Instagram: ' + str(ig_id) if ig_id else '⚠ Instagram: skipped'}")

        # 5. Facebook
        step = "Facebook Upload"
        print(f"\n[5/5] {step}...")
        from facebook_uploader import upload_to_facebook
        fb_id = upload_to_facebook(video_path, content_data)
        print(f"  {'✓ Facebook: ' + str(fb_id) if fb_id else '⚠ Facebook: skipped'}")

        _log_upload(youtube_id, content_data, {
            "youtube":   youtube_id,
            "instagram": ig_id,
            "facebook":  fb_id,
        })

        print("\n" + "═" * 60)
        print(f"  ✅ PIPELINE COMPLETE — {label}")
        print("═" * 60 + "\n")

    except (Exception, SystemExit) as exc:
        is_sys_exit = isinstance(exc, SystemExit)
        if is_sys_exit and exc.code == 0:
            sys.exit(0)
            
        log.error(f"Pipeline FAILED at [{step}]: {exc}", exc_info=not is_sys_exit)
        _log_failure(step, str(exc))
        try:
            from notifier import send_error_alert
            send_error_alert(exc, step, content_data)
            print(f"  📧 Error email sent to {log.root.handlers}")
        except Exception as mail_err:
            log.warning(f"Could not send error email: {mail_err}")

        print("\n" + "═" * 60)
        print(f"  ❌ PIPELINE FAILED — {step} | Audience: {TARGET_AUDIENCE}")
        print("═" * 60 + "\n")
        sys.exit(exc.code if is_sys_exit and isinstance(exc.code, int) else 1)

    finally:
        if video_path and video_path.exists():
            try:
                video_path.unlink()
            except Exception:
                pass


if __name__ == "__main__":
    run()
