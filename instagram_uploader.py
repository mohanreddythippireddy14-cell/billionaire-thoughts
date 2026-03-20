# instagram_uploader.py
# ============================================================
# Uploads video to Instagram as a Reel via Instagram Graph API
#
# SETUP REQUIRED (one time):
#   1. You need an Instagram Professional (Creator/Business) account
#   2. It must be connected to a Facebook Page
#   3. Create a Facebook App at developers.facebook.com
#   4. Get a long-lived access token (lasts 60 days)
#   5. Add INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_USER_ID to GitHub Secrets
#
# If credentials are not set, this step is silently skipped —
# YouTube upload still happens normally.
# ============================================================

import logging
import os
import time

import requests

log = logging.getLogger("InstagramUploader")

INSTAGRAM_ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
INSTAGRAM_USER_ID      = os.environ.get("INSTAGRAM_USER_ID",      "")
GRAPH_API_VERSION      = "v18.0"


def upload_to_instagram(video_path, content_data: dict) -> str | None:
    """
    Upload video to Instagram as a Reel.
    Returns Instagram media ID if successful, None if skipped/failed.
    """
    if not INSTAGRAM_ACCESS_TOKEN or not INSTAGRAM_USER_ID:
        log.info("Instagram credentials not configured — skipping.")
        log.info("To enable: add INSTAGRAM_ACCESS_TOKEN + INSTAGRAM_USER_ID to GitHub Secrets.")
        return None

    caption = (
        f"{content_data.get('content', '')}\n\n"
        "💰 Follow for daily wealth secrets\n\n"
        "#finance #money #wealth #millionaire #reels "
        "#moneymindset #rich #billionaire #financialfreedom #shorts"
    )

    try:
        # Step 1: Upload video to a temporary public URL
        # Instagram requires a public HTTPS URL — we use file.io (free, no account)
        log.info("Uploading video to temporary host (file.io)...")
        video_url = _temp_url(video_path)
        if not video_url:
            log.error("Could not get temporary URL — Instagram upload skipped.")
            return None

        base = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{INSTAGRAM_USER_ID}"

        # Step 2: Create media container
        log.info("Creating Instagram media container...")
        r = requests.post(f"{base}/media", data={
            "media_type":    "REELS",
            "video_url":     video_url,
            "caption":       caption,
            "share_to_feed": "true",
            "access_token":  INSTAGRAM_ACCESS_TOKEN,
        }, timeout=60)
        r.raise_for_status()
        container_id = r.json()["id"]

        # Step 3: Wait for Instagram to process the video
        log.info(f"Waiting for Instagram to process video (container={container_id})...")
        for attempt in range(36):            # up to 6 minutes
            time.sleep(10)
            sr = requests.get(
                f"https://graph.facebook.com/{GRAPH_API_VERSION}/{container_id}",
                params={"fields": "status_code", "access_token": INSTAGRAM_ACCESS_TOKEN},
                timeout=30,
            )
            status = sr.json().get("status_code", "")
            log.info(f"  Processing status: {status} (attempt {attempt + 1}/36)")
            if status == "FINISHED":
                break
            if status == "ERROR":
                raise RuntimeError("Instagram video processing returned ERROR.")
        else:
            raise TimeoutError("Instagram video processing timed out after 6 minutes.")

        # Step 4: Publish the Reel
        log.info("Publishing Reel...")
        pr = requests.post(f"{base}/media_publish", data={
            "creation_id": container_id,
            "access_token": INSTAGRAM_ACCESS_TOKEN,
        }, timeout=60)
        pr.raise_for_status()
        media_id = pr.json()["id"]
        log.info(f"Instagram Reel published: {media_id}")
        return media_id

    except Exception as exc:
        log.error(f"Instagram upload failed: {exc}")
        # We return None — the pipeline continues; YouTube is still uploaded
        return None


def _temp_url(video_path) -> str | None:
    """
    Upload video to file.io to get a temporary public HTTPS URL.
    The URL expires after 1 hour (enough time for Instagram to fetch it).
    """
    try:
        with open(video_path, "rb") as f:
            resp = requests.post(
                "https://file.io/?expires=1h",
                files={"file": ("video.mp4", f, "video/mp4")},
                timeout=120,
            )
        data = resp.json()
        if data.get("success"):
            log.info(f"Temp URL obtained: {data['link'][:60]}...")
            return data["link"]
        log.error(f"file.io returned: {data}")
    except Exception as exc:
        log.error(f"file.io upload failed: {exc}")
    return None
