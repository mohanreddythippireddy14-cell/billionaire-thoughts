# facebook_uploader.py
# ============================================================
# Uploads video to a Facebook Page as a Reel
#
# SETUP REQUIRED (one time):
#   1. Create a Facebook Page for your channel
#   2. Create a Facebook App at developers.facebook.com
#   3. Add 'pages_manage_posts' and 'pages_read_engagement' permissions
#   4. Get a Page Access Token (long-lived, lasts ~60 days)
#   5. Add FACEBOOK_ACCESS_TOKEN and FACEBOOK_PAGE_ID to GitHub Secrets
#
# If credentials are not set, this step is silently skipped.
# ============================================================

import logging
import os

import requests

log = logging.getLogger("FacebookUploader")

FACEBOOK_ACCESS_TOKEN = os.environ.get("FACEBOOK_ACCESS_TOKEN", "")
FACEBOOK_PAGE_ID      = os.environ.get("FACEBOOK_PAGE_ID",      "")
GRAPH_VERSION         = "v18.0"


def upload_to_facebook(video_path, content_data: dict) -> str | None:
    """
    Upload video to Facebook Page.
    Returns the video ID if successful, None if skipped/failed.
    """
    if not FACEBOOK_ACCESS_TOKEN or not FACEBOOK_PAGE_ID:
        log.info("Facebook credentials not configured — skipping.")
        log.info("To enable: add FACEBOOK_ACCESS_TOKEN + FACEBOOK_PAGE_ID to GitHub Secrets.")
        return None

    description = (
        f"{content_data.get('content', '')}\n\n"
        "💰 Follow for daily wealth secrets\n\n"
        "#finance #money #wealth #millionaire #moneymindset #rich #billionaire"
    )

    try:
        file_size = video_path.stat().st_size
        upload_url = f"https://graph.facebook.com/{GRAPH_VERSION}/{FACEBOOK_PAGE_ID}/videos"

        # Step 1: Start upload session
        log.info("Starting Facebook video upload session...")
        init = requests.post(upload_url, data={
            "upload_phase":  "start",
            "file_size":     file_size,
            "access_token":  FACEBOOK_ACCESS_TOKEN,
        }, timeout=30)
        init.raise_for_status()
        init_data = init.json()
        session_id   = init_data["upload_session_id"]
        video_id     = init_data["video_id"]
        start_offset = int(init_data["start_offset"])
        end_offset   = int(init_data["end_offset"])
        log.info(f"Upload session started (video_id={video_id})")

        # Step 2: Upload file in chunks
        log.info(f"Uploading {file_size // 1024}KB to Facebook...")
        with open(video_path, "rb") as fh:
            while start_offset < file_size:
                fh.seek(start_offset)
                chunk = fh.read(end_offset - start_offset)
                cr = requests.post(upload_url, data={
                    "upload_phase":     "transfer",
                    "upload_session_id": session_id,
                    "start_offset":     start_offset,
                    "access_token":     FACEBOOK_ACCESS_TOKEN,
                }, files={"video_file_chunk": chunk}, timeout=120)
                cr.raise_for_status()
                cd = cr.json()
                start_offset = int(cd["start_offset"])
                end_offset   = int(cd["end_offset"])
                pct = int(start_offset / file_size * 100)
                log.info(f"  {pct}% uploaded...")

        # Step 3: Finish upload and set description
        log.info("Finishing Facebook upload...")
        fin = requests.post(upload_url, data={
            "upload_phase":     "finish",
            "upload_session_id": session_id,
            "description":      description,
            "access_token":     FACEBOOK_ACCESS_TOKEN,
        }, timeout=60)
        fin.raise_for_status()
        log.info(f"Facebook video uploaded: video_id={video_id}")
        return str(video_id)

    except Exception as exc:
        log.error(f"Facebook upload failed: {exc}")
        return None
