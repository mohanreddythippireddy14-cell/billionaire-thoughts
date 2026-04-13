# youtube_uploader.py
# ============================================================
# Uploads video to YouTube using OAuth2 (Data API v3)
# ============================================================

import json
import logging
from pathlib import Path

from tenacity import (
    before_sleep_log, retry, retry_if_exception,
    stop_after_attempt, wait_exponential,
)

from config import (
    CHANNEL_EMOJI, CHANNEL_NAME, DESCRIPTION_CTA,
    YOUTUBE_CATEGORY_ID, YOUTUBE_CLIENT_SECRET,
    YOUTUBE_DESCRIPTION_TEMPLATE, YOUTUBE_HASHTAGS,
    YOUTUBE_LANGUAGE, YOUTUBE_PRIVACY,
    YOUTUBE_TAGS, YOUTUBE_TOKEN_FILE,
)

log = logging.getLogger("YouTubeUploader")


def _is_retryable(exc: Exception) -> bool:
    try:
        from googleapiclient.errors import HttpError
        if isinstance(exc, HttpError):
            code = int(getattr(getattr(exc, "resp", None), "status", 0))
            return code in {429, 500, 502, 503, 504}
    except ImportError:
        pass
    return isinstance(exc, (TimeoutError, ConnectionError, OSError))


def _build_client():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    import os
    import sys

    try:
        is_ci = os.environ.get("GITHUB_ACTIONS") == "true"
        
        if is_ci:
            token_json = os.environ.get("YOUTUBE_TOKEN_JSON")
            if not token_json:
                raise ValueError("YOUTUBE_TOKEN_JSON environment variable is not set in CI.")
            raw = json.loads(token_json)
        else:
            if not YOUTUBE_TOKEN_FILE.exists():
                raise FileNotFoundError(
                    f"youtube_token.json not found.\n"
                    "Run setup_auth.py → update YOUTUBE_TOKEN_JSON in GitHub Secrets."
                )
            raw = json.loads(YOUTUBE_TOKEN_FILE.read_text(encoding="utf-8"))

        creds = Credentials(
            token         = raw.get("token"),
            refresh_token = raw.get("refresh_token"),
            token_uri     = raw.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id     = raw.get("client_id"),
            client_secret = raw.get("client_secret"),
            scopes        = raw.get("scopes", ["https://www.googleapis.com/auth/youtube.upload"]),
        )
        
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Save the refreshed token back to disk if not in CI
            if not is_ci:
                YOUTUBE_TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
                
        return build("youtube", "v3", credentials=creds)

    except Exception as e:
        is_refresh_error = type(e).__name__ == "RefreshError" or "invalid_grant" in str(e)
        if is_refresh_error:
            msg = "YouTube token expired. Re-authentication required."
            log.error(msg)
            sys.exit(msg)
        raise



@retry(
    reraise=True,
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=2, min=5, max=60),
    retry=retry_if_exception(_is_retryable),
    before_sleep=before_sleep_log(log, logging.WARNING),
)
def upload_to_youtube(video_path: Path, content_data: dict) -> str:
    """Upload video to YouTube. Returns the video ID."""
    from googleapiclient.http import MediaFileUpload

    youtube = _build_client()

    title        = content_data.get("title", f"Hard Truth 😎 | {CHANNEL_NAME}")[:100]
    hashtags_str = " ".join(YOUTUBE_HASHTAGS)

    # Use hook as the on-screen text and answer as the description content
    screen_text  = content_data.get("hook", content_data.get("content", ""))

    description = YOUTUBE_DESCRIPTION_TEMPLATE.format(
        content       = screen_text,
        description_cta = DESCRIPTION_CTA,
        channel       = CHANNEL_NAME,
        emoji         = CHANNEL_EMOJI,
        hashtags      = hashtags_str,
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

    log.info(f"Uploading: {title[:60]}...")
    request  = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None

    while response is None:
        status, response = request.next_chunk()
        if status:
            log.info(f"  Upload progress: {int(status.progress() * 100)}%")

    video_id = response["id"]
    log.info(f"Uploaded → https://youtube.com/shorts/{video_id}")
    return video_id
