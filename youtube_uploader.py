# youtube_uploader.py
# ============================================================
# Uploads video to YouTube using OAuth2 (Data API v3)
#
# How the token works:
#   - You run setup_auth.py ONCE on your Windows PC
#   - It opens a browser, you log in, it saves youtube_token.json
#   - You copy that file's contents into a GitHub Secret
#   - GitHub Actions decodes it and places it as youtube_token.json
#   - The refresh_token inside it lasts forever (until you revoke it)
#   - This file auto-refreshes the access_token every hour
# ============================================================

import json
import logging
from pathlib import Path

from tenacity import (
    before_sleep_log, retry, retry_if_exception,
    stop_after_attempt, wait_exponential,
)

from config import (
    CHANNEL_EMOJI, CHANNEL_NAME, YOUTUBE_CATEGORY_ID, YOUTUBE_CLIENT_SECRET,
    YOUTUBE_DESCRIPTION_TEMPLATE, YOUTUBE_HASHTAGS, YOUTUBE_LANGUAGE,
    YOUTUBE_PRIVACY, YOUTUBE_TAGS, YOUTUBE_TOKEN_FILE,
)

log = logging.getLogger("YouTubeUploader")


def _is_retryable(exc: Exception) -> bool:
    """Return True for transient errors worth retrying."""
    try:
        from googleapiclient.errors import HttpError
        if isinstance(exc, HttpError):
            code = int(getattr(getattr(exc, "resp", None), "status", 0))
            return code in {429, 500, 502, 503, 504}
    except ImportError:
        pass
    return isinstance(exc, (TimeoutError, ConnectionError, OSError))


def _build_client():
    """Build an authenticated YouTube API client from the saved token."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    if not YOUTUBE_TOKEN_FILE.exists():
        raise FileNotFoundError(
            f"youtube_token.json not found at {YOUTUBE_TOKEN_FILE}\n"
            "Fix:\n"
            "  1. Run setup_auth.py on your Windows PC\n"
            "  2. Copy the base64 output into GitHub Secret YOUTUBE_TOKEN_JSON\n"
            "  See SETUP_GUIDE.md for full instructions."
        )

    raw   = json.loads(YOUTUBE_TOKEN_FILE.read_text(encoding="utf-8"))
    creds = Credentials(
        token         = raw.get("token"),
        refresh_token = raw.get("refresh_token"),
        token_uri     = raw.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id     = raw.get("client_id"),
        client_secret = raw.get("client_secret"),
        scopes        = raw.get("scopes", ["https://www.googleapis.com/auth/youtube.upload"]),
    )

    # Auto-refresh access token if expired
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

    return build("youtube", "v3", credentials=creds)


@retry(
    reraise=True,
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=2, min=5, max=60),
    retry=retry_if_exception(_is_retryable),
    before_sleep=before_sleep_log(log, logging.WARNING),
)
def upload_to_youtube(video_path: Path, content_data: dict) -> str:
    """
    Upload video to YouTube.
    Returns the YouTube video ID.
    """
    from googleapiclient.http import MediaFileUpload

    youtube = _build_client()

    title = content_data.get("title", f"Hard Truth 😎 | {CHANNEL_NAME}")[:100]

    # Build hashtags string — joins list into spaced hashtags
    hashtags_str = " ".join(YOUTUBE_HASHTAGS)

    description = YOUTUBE_DESCRIPTION_TEMPLATE.format(
        content  = content_data.get("content", ""),
        channel  = CHANNEL_NAME,
        emoji    = CHANNEL_EMOJI,
        hashtags = hashtags_str,
    )

    body = {
        "snippet": {
            "title":           title,
            "description":     description,
            "tags":            YOUTUBE_TAGS,
            "categoryId":      YOUTUBE_CATEGORY_ID,
            "defaultLanguage": YOUTUBE_LANGUAGE,
        },
        "status": {
            "privacyStatus":           YOUTUBE_PRIVACY,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        str(video_path),
        mimetype  = "video/mp4",
        resumable = True,
        chunksize = 1024 * 1024,
    )

    log.info(f"Uploading to YouTube: {title[:60]}...")
    request  = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None

    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            log.info(f"  Upload progress: {pct}%")

    video_id = response["id"]
    log.info(f"YouTube upload done → https://youtube.com/shorts/{video_id}")
    return video_id
