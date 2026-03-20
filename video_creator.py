# video_creator.py
# ============================================================
# Creates the final video using Pexels video backgrounds + FFmpeg
#
# Video structure:
#   ┌─────────────────────────────────────┐
#   │  Intro     (2s)  — channel branding │
#   │  Main     (22s)  — cinematic video  │  ← Pexels background
#   │  Outro     (3s)  — follow CTA       │
#   └─────────────────────────────────────┘
#   Total: ~27 seconds — perfect for YouTube Shorts
#   Format: 1080×1920 (9:16 portrait), 30fps, H.264
#
# Background selection:
#   - Fetches dark cinematic video from Pexels API based on mood
#   - Falls back to gradient if Pexels API unavailable
#   - Text overlay rendered with Pillow, composited with FFmpeg
# ============================================================

import logging
import os
import random
import shutil
import subprocess
import time
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

from config import (
    CHANNEL_NAME, FONTS_DIR, INTRO_DURATION_SECONDS,
    MAIN_DURATION_SECONDS, MUSIC_DIR,
    OUTRO_DURATION_SECONDS, TEMP_DIR, VIDEO_FPS,
    VIDEO_HEIGHT, VIDEO_WIDTH, VISUAL_THEMES,
)

log = logging.getLogger("VideoCreator")

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")

# Mood → Pexels search queries (multiple for variety)
MOOD_QUERIES = {
    "dark_truth": [
        "dark silhouette man", "dark forest night", "dark shadow cinematic",
        "lone man walking night", "dark rain city", "shadow figure dramatic",
    ],
    "mindset": [
        "mountain peak fog", "dark sky storm", "man standing cliff",
        "dark ocean waves", "silhouette warrior", "dark clouds moving",
    ],
    "wealth_fact": [
        "city lights night", "skyscraper dark", "businessman night city",
        "dark luxury", "night skyline", "dark office building",
    ],
}


# ── Fonts ─────────────────────────────────────────────────────

def _font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    candidates = [
        FONTS_DIR / ("Montserrat-Bold.ttf" if bold else "Montserrat-Regular.ttf"),
        FONTS_DIR / "Montserrat-Bold.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ]
    for p in candidates:
        try:
            return ImageFont.truetype(str(p), size)
        except Exception:
            continue
    return ImageFont.load_default()


def _emoji_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        Path("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"),
        Path("/usr/share/fonts/noto/NotoColorEmoji.ttf"),
        Path("/usr/share/fonts/truetype/noto-color-emoji/NotoColorEmoji.ttf"),
    ]
    for p in candidates:
        try:
            return ImageFont.truetype(str(p), size)
        except Exception:
            continue
    return _font(size)


# ── Pexels Video Fetcher ──────────────────────────────────────

def _fetch_pexels_video(mood: str) -> Path | None:
    """
    Fetch a dark cinematic portrait video from Pexels.
    Downloads to TEMP_DIR. Returns path or None on failure.
    """
    if not PEXELS_API_KEY:
        log.warning("PEXELS_API_KEY not set — using gradient fallback")
        return None

    queries = MOOD_QUERIES.get(mood, MOOD_QUERIES["dark_truth"])
    query   = random.choice(queries)

    try:
        log.info(f"Fetching Pexels video: '{query}'...")
        resp = requests.get(
            "https://api.pexels.com/videos/search",
            headers={"Authorization": PEXELS_API_KEY},
            params={
                "query":       query,
                "orientation": "portrait",
                "size":        "medium",
                "per_page":    15,
            },
            timeout=20,
        )
        resp.raise_for_status()
        videos = resp.json().get("videos", [])

        if not videos:
            # Fallback query
            resp2  = requests.get(
                "https://api.pexels.com/videos/search",
                headers={"Authorization": PEXELS_API_KEY},
                params={"query": "dark night", "orientation": "portrait", "per_page": 10},
                timeout=20,
            )
            resp2.raise_for_status()
            videos = resp2.json().get("videos", [])

        if not videos:
            log.warning("No Pexels videos found — using gradient fallback")
            return None

        video    = random.choice(videos[:10])
        video_id = video["id"]
        files    = video.get("video_files", [])

        # Prefer portrait files, then pick highest resolution
        portrait = [f for f in files if f.get("width", 0) < f.get("height", 1)]
        chosen   = (
            max(portrait, key=lambda f: f.get("width", 0))
            if portrait
            else max(files, key=lambda f: f.get("width", 0))
        )

        video_url = chosen.get("link", "")
        if not video_url:
            log.warning("No valid video URL — using gradient fallback")
            return None

        dest = TEMP_DIR / f"pexels_{video_id}_{int(time.time())}.mp4"
        log.info(f"Downloading Pexels video {video_id}...")
        dl = requests.get(video_url, timeout=60, stream=True)
        dl.raise_for_status()
        with open(dest, "wb") as fh:
            for chunk in dl.iter_content(chunk_size=1024 * 256):
                fh.write(chunk)

        log.info(f"Downloaded: {dest.name} ({dest.stat().st_size // 1024} KB)")
        return dest

    except Exception as exc:
        log.warning(f"Pexels fetch failed: {exc} — using gradient fallback")
        return None


# ── Background helpers ────────────────────────────────────────

def _make_gradient(theme: dict) -> Image.Image:
    """Fallback cinematic dark gradient."""
    img  = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT))
    draw = ImageDraw.Draw(img)
    top, bot = theme["bg_top"], theme["bg_bottom"]
    for y in range(VIDEO_HEIGHT):
        t = y / VIDEO_HEIGHT
        r = int(top[0] + (bot[0] - top[0]) * t)
        g = int(top[1] + (bot[1] - top[1]) * t)
        b = int(top[2] + (bot[2] - top[2]) * t)
        draw.line([(0, y), (VIDEO_WIDTH, y)], fill=(r, g, b))
    return img


def _make_video_background_clip(video_path: Path, duration: float,
                                 out_path: Path) -> Path:
    """
    Crop Pexels video to 9:16, scale to 1080×1920,
    darken by 55% so text is readable, trim to duration.
    """
    _check_ffmpeg()
    vf = (
        f"crop=ih*9/16:ih,"
        f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT},"
        f"setsar=1,"
        f"colorchannelmixer=rr=0.45:gg=0.45:bb=0.45"
    )
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vf", vf,
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-r", str(VIDEO_FPS),
        "-an",
        str(out_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg background error:\n{result.stderr[-600:]}")
    return out_path


# ── Text overlay ──────────────────────────────────────────────

def _wrap(text: str, font, max_px: int, draw: ImageDraw.Draw) -> list[str]:
    words, lines, current = text.split(), [], []
    for word in words:
        test_line = " ".join(current + [word])
        w = draw.textbbox((0, 0), test_line, font=font)[2]
        if w <= max_px:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines


def _make_text_overlay(content_data: dict) -> Path:
    """
    Render text as transparent RGBA PNG.
    Composited on top of the Pexels video via FFmpeg overlay filter.
    """
    mood    = content_data.get("mood", "dark_truth")
    content = content_data["content"]
    theme   = VISUAL_THEMES.get(mood, VISUAL_THEMES["dark_truth"])

    img    = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 0))
    draw   = ImageDraw.Draw(img)
    cx     = VIDEO_WIDTH // 2
    accent = theme["accent_color"]

    # Top accent bar
    draw.rectangle([0, 0, VIDEO_WIDTH, 6], fill=(*accent, 230))
    draw.rectangle([0, VIDEO_HEIGHT - 6, VIDEO_WIDTH, VIDEO_HEIGHT],
                   fill=(*accent, 230))

    # Channel watermark strip
    draw.rectangle([0, 20, VIDEO_WIDTH, 100], fill=(0, 0, 0, 170))
    draw.text((cx, 60), "BillionAire's _Thoughts",
              font=_font(36, bold=False), anchor="mm",
              fill=(*accent, 240))

    # Mood label strip
    draw.rectangle([0, 100, VIDEO_WIDTH, 148], fill=(0, 0, 0, 140))
    draw.text((cx, 124), theme["label"],
              font=_font(30, bold=True), anchor="mm",
              fill=(*accent, 230))

    draw.line([(60, 153), (VIDEO_WIDTH - 60, 153)],
              fill=(*accent, 180), width=2)

    # Main content text
    content_font = _font(72, bold=True)
    padding_x    = 70
    max_px       = VIDEO_WIDTH - padding_x * 2
    lines        = _wrap(content, content_font, max_px, draw)
    line_h       = 108
    block_h      = len(lines) * line_h
    start_y      = int(VIDEO_HEIGHT * 0.30)

    for i, line in enumerate(lines):
        y    = start_y + i * line_h
        bbox = draw.textbbox((cx, y), line, font=content_font, anchor="mm")

        # Dark pill behind text for readability on any background
        draw.rectangle(
            [bbox[0] - 16, bbox[1] - 8, bbox[2] + 16, bbox[3] + 8],
            fill=(0, 0, 0, 175),
        )
        # Shadow
        for dx, dy in [(-2, 2), (2, 2), (-2, -2), (2, -2)]:
            draw.text((cx + dx, y + dy), line,
                      font=content_font, anchor="mm", fill=(0, 0, 0, 200))
        # Main text — always white for maximum contrast
        draw.text((cx, y), line,
                  font=content_font, anchor="mm", fill=(255, 255, 255, 255))

    # Divider
    sep_y = start_y + block_h + 40
    draw.line([(60, sep_y), (VIDEO_WIDTH - 60, sep_y)],
              fill=(*accent, 180), width=2)

    # Bottom CTA
    draw.rectangle([0, VIDEO_HEIGHT - 165, VIDEO_WIDTH, VIDEO_HEIGHT - 95],
                   fill=(0, 0, 0, 160))
    draw.text((cx, VIDEO_HEIGHT - 130),
              "Follow for daily hard truths",
              font=_font(38, bold=False), anchor="mm",
              fill=(220, 220, 220, 235))

    path = TEMP_DIR / "overlay_main.png"
    img.save(str(path), "PNG")
    return path


# ── Frame creators (intro/outro — static gradient) ────────────

def _intro_frame() -> Path:
    img  = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    for y in range(VIDEO_HEIGHT):
        t = y / VIDEO_HEIGHT
        draw.line([(0, y), (VIDEO_WIDTH, y)],
                  fill=(int(22 * (1 - t)), int(16 * (1 - t)), 0))

    cx, cy = VIDEO_WIDTH // 2, VIDEO_HEIGHT // 2
    gold   = (255, 210, 0)
    draw.line([(80, cy - 140), (VIDEO_WIDTH - 80, cy - 140)], fill=gold, width=3)
    draw.line([(80, cy + 140), (VIDEO_WIDTH - 80, cy + 140)], fill=gold, width=3)

    try:
        draw.text((cx, cy - 190), "💰", font=_emoji_font(120),
                  anchor="mm", fill=gold)
    except Exception:
        draw.text((cx, cy - 190), "$", font=_font(110), anchor="mm", fill=gold)

    draw.text((cx, cy - 20), "BillionAire's",
              font=_font(82, bold=True), anchor="mm", fill=gold)
    draw.text((cx, cy + 80), "_Thoughts",
              font=_font(64, bold=False), anchor="mm", fill=(200, 200, 200))

    path = TEMP_DIR / "frame_intro.png"
    img.save(str(path), "PNG")
    return path


def _outro_frame() -> Path:
    img  = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    for y in range(VIDEO_HEIGHT):
        t = y / VIDEO_HEIGHT
        draw.line([(0, y), (VIDEO_WIDTH, y)],
                  fill=(int(22 * (1 - t)), int(16 * (1 - t)), 0))

    cx, cy = VIDEO_WIDTH // 2, VIDEO_HEIGHT // 2
    gold   = (255, 210, 0)

    draw.text((cx, cy - 180), "Follow for more",
              font=_font(68, bold=True), anchor="mm", fill=(255, 255, 255))
    try:
        draw.text((cx, cy - 40), "💰",
                  font=_emoji_font(130), anchor="mm", fill=gold)
    except Exception:
        draw.text((cx, cy - 40), "$", font=_font(110), anchor="mm", fill=gold)

    draw.text((cx, cy + 110), CHANNEL_NAME,
              font=_font(58, bold=True), anchor="mm", fill=gold)
    draw.text((cx, cy + 200), "New video every evening",
              font=_font(40, bold=False), anchor="mm", fill=(160, 160, 160))

    path = TEMP_DIR / "frame_outro.png"
    img.save(str(path), "PNG")
    return path


# ── FFmpeg helpers ────────────────────────────────────────────

def _check_ffmpeg():
    if not shutil.which("ffmpeg"):
        raise EnvironmentError(
            "FFmpeg not found!\n"
            "GitHub Actions: add to upload.yml:\n"
            "  - run: sudo apt-get install -y ffmpeg"
        )


def _image_to_clip(img_path: Path, duration: float, out_path: Path) -> Path:
    """Convert static PNG to video clip."""
    _check_ffmpeg()
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(img_path),
        "-vf", f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT},setsar=1",
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-r", str(VIDEO_FPS),
        str(out_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg image clip error:\n{result.stderr[-600:]}")
    return out_path


def _overlay_text_on_video(video_clip: Path, overlay_png: Path,
                            out_path: Path) -> Path:
    """Composite transparent text overlay PNG on top of video clip."""
    _check_ffmpeg()
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_clip),
        "-i", str(overlay_png),
        "-filter_complex", "[0:v][1:v]overlay=0:0[v]",
        "-map", "[v]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-r", str(VIDEO_FPS),
        str(out_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg overlay error:\n{result.stderr[-600:]}")
    return out_path


def _pick_music() -> Path:
    exts   = {".mp3", ".wav", ".m4a", ".aac", ".ogg"}
    tracks = [p for p in MUSIC_DIR.iterdir() if p.suffix.lower() in exts]
    if not tracks:
        raise FileNotFoundError(
            f"No music in {MUSIC_DIR}/\n"
            "Add MP3 files to music/ and commit to GitHub."
        )
    return min(tracks, key=lambda p: p.stat().st_atime)


# ── Main entry point ──────────────────────────────────────────

def create_video(content_data: dict) -> Path:
    """
    Full pipeline:
      Intro (2s gradient) +
      Main (22s Pexels video + text overlay) +
      Outro (3s gradient) +
      Trap music
    Falls back to gradient if Pexels unavailable.
    """
    _check_ffmpeg()
    ts   = int(time.time())
    mood = content_data.get("mood", "dark_truth")
    log.info(f"Creating video — mood: {mood}")

    pexels_raw  = None
    bg_clip     = TEMP_DIR / f"bg_clip_{ts}.mp4"
    main_mp4    = TEMP_DIR / f"clip_main_{ts}.mp4"
    intro_mp4   = TEMP_DIR / f"clip_intro_{ts}.mp4"
    outro_mp4   = TEMP_DIR / f"clip_outro_{ts}.mp4"
    concat_mp4  = TEMP_DIR / f"concat_{ts}.mp4"
    concat_txt  = TEMP_DIR / f"concat_{ts}.txt"
    final_mp4   = TEMP_DIR / f"video_{ts}.mp4"
    combined_p  = TEMP_DIR / f"combined_{ts}.png"

    try:
        # 1. Render static frames
        intro_png   = _intro_frame()
        outro_png   = _outro_frame()
        overlay_png = _make_text_overlay(content_data)

        # 2. Fetch Pexels background
        pexels_raw = _fetch_pexels_video(mood)

        if pexels_raw and pexels_raw.exists():
            _make_video_background_clip(
                pexels_raw, float(MAIN_DURATION_SECONDS), bg_clip
            )
            _overlay_text_on_video(bg_clip, overlay_png, main_mp4)
        else:
            # Gradient fallback
            theme    = VISUAL_THEMES.get(mood, VISUAL_THEMES["dark_truth"])
            grad_img = _make_gradient(theme)
            overlay  = Image.open(str(overlay_png)).convert("RGBA")
            combined = Image.alpha_composite(
                grad_img.convert("RGBA"), overlay
            ).convert("RGB")
            combined.save(str(combined_p), "PNG")
            _image_to_clip(combined_p, float(MAIN_DURATION_SECONDS), main_mp4)

        # 3. Intro + outro clips
        _image_to_clip(intro_png, float(INTRO_DURATION_SECONDS), intro_mp4)
        _image_to_clip(outro_png, float(OUTRO_DURATION_SECONDS), outro_mp4)

        # 4. Concatenate
        concat_txt.write_text(
            f"file '{intro_mp4.resolve()}'\n"
            f"file '{main_mp4.resolve()}'\n"
            f"file '{outro_mp4.resolve()}'\n"
        )
        result = subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_txt), "-c", "copy", str(concat_mp4),
        ], capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f"Concat error:\n{result.stderr[-600:]}")

        # 5. Add music
        music      = _pick_music()
        total_dur  = INTRO_DURATION_SECONDS + MAIN_DURATION_SECONDS + OUTRO_DURATION_SECONDS
        fade_start = total_dur - 2

        result = subprocess.run([
            "ffmpeg", "-y",
            "-i", str(concat_mp4),
            "-stream_loop", "-1", "-i", str(music),
            "-map", "0:v", "-map", "1:a",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-af", f"volume=0.3,afade=t=out:st={fade_start}:d=2",
            "-t", str(total_dur),
            str(final_mp4),
        ], capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f"Music error:\n{result.stderr[-600:]}")

        log.info(f"Video ready: {final_mp4.name}")
        return final_mp4

    finally:
        for f in [bg_clip, main_mp4, intro_mp4, outro_mp4,
                  concat_mp4, concat_txt, combined_p]:
            try:
                Path(f).unlink(missing_ok=True)
            except Exception:
                pass
        if pexels_raw:
            try:
                pexels_raw.unlink(missing_ok=True)
            except Exception:
                pass
