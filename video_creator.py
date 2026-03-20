# video_creator.py
# ============================================================
# Creates the final video using Pillow (images) + FFmpeg (video)
#
# Video structure:
#   ┌─────────────────────────────────────┐
#   │  Intro     (2s)  — channel branding │
#   │  Main     (22s)  — finance content  │
#   │  Outro     (3s)  — follow CTA       │
#   └─────────────────────────────────────┘
#   Total: ~27 seconds — perfect for YouTube Shorts
#   Format: 1080×1920 (9:16 portrait), 30fps, H.264
# ============================================================

import logging
import shutil
import subprocess
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from config import (
    CHANNEL_NAME, FONTS_DIR, INTRO_DURATION_SECONDS,
    LOGS_DIR, MAIN_DURATION_SECONDS, MUSIC_DIR,
    OUTRO_DURATION_SECONDS, TEMP_DIR, VIDEO_FPS,
    VIDEO_HEIGHT, VIDEO_WIDTH, VISUAL_THEMES,
)

log = logging.getLogger("VideoCreator")


# ── Fonts ─────────────────────────────────────────────────────

def _font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    """
    Load font. Tries Montserrat first, then DejaVu (always on GitHub Actions),
    then NotoSans, then PIL fallback.
    """
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
    log.warning("No TTF font found — using PIL default")
    return ImageFont.load_default()


def _emoji_font(size: int) -> ImageFont.FreeTypeFont:
    """Load Noto Color Emoji font for proper emoji rendering."""
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
    # Fallback to regular font — emoji will show as □ but won't crash
    return _font(size)


# ── Background ────────────────────────────────────────────────

def _make_gradient(theme: dict) -> Image.Image:
    """Create a cinematic dark gradient background."""
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


# ── Text helpers ──────────────────────────────────────────────

def _wrap(text: str, font, max_px: int, draw: ImageDraw.Draw) -> list[str]:
    """Word-wrap text to fit within max_px width."""
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


def _draw_glow(draw: ImageDraw.Draw, text: str, x: int, y: int,
               font, glow_color: tuple, radius: int = 18):
    """
    Draw a soft cinematic glow behind text.
    Uses RGBA image compositing so the glow is genuinely semi-transparent —
    no hard rectangular highlight boxes.
    """
    # Build glow on a separate RGBA layer, then composite onto the main image
    glow_layer = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 0))
    glow_draw  = ImageDraw.Draw(glow_layer)

    for r in range(radius, 0, -3):
        alpha = int(80 * (1 - r / radius))   # fade out as radius grows
        color = (*glow_color, alpha)
        for dx in range(-r, r + 1, max(1, r // 3)):
            for dy in range(-r, r + 1, max(1, r // 3)):
                glow_draw.text(
                    (x + dx, y + dy), text,
                    font=font, anchor="mm", fill=color,
                )

    # Composite glow onto the existing draw context's image
    base = draw._image  # access underlying image
    base.paste(
        Image.alpha_composite(base.convert("RGBA"), glow_layer).convert("RGB"),
        (0, 0),
    )


def _draw_text_safe(draw: ImageDraw.Draw, pos: tuple, text: str,
                    font, fill: tuple, anchor: str = "mm"):
    """Draw text — strips emoji if emoji font not available to avoid crashes."""
    try:
        draw.text(pos, text, font=font, anchor=anchor, fill=fill)
    except Exception:
        # Strip non-ASCII as fallback
        safe = text.encode("ascii", "ignore").decode("ascii").strip()
        draw.text(pos, safe, font=font, anchor=anchor, fill=fill)


# ── Frame creators ────────────────────────────────────────────

def _intro_frame() -> Path:
    """2-second branded intro — gold branding on black."""
    img  = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Subtle dark gold gradient
    for y in range(VIDEO_HEIGHT):
        t = y / VIDEO_HEIGHT
        r = int(22 * (1 - t))
        g = int(16 * (1 - t))
        draw.line([(0, y), (VIDEO_WIDTH, y)], fill=(r, g, 0))

    cx   = VIDEO_WIDTH  // 2
    cy   = VIDEO_HEIGHT // 2
    gold = (255, 210, 0)

    # Gold accent lines
    draw.line([(80, cy - 140), (VIDEO_WIDTH - 80, cy - 140)], fill=gold, width=3)
    draw.line([(80, cy + 140), (VIDEO_WIDTH - 80, cy + 140)], fill=gold, width=3)

    # Money bag emoji
    try:
        draw.text((cx, cy - 190), "💰", font=_emoji_font(120),
                  anchor="mm", fill=gold)
    except Exception:
        draw.text((cx, cy - 190), "$", font=_font(110), anchor="mm", fill=gold)

    # Channel name
    draw.text((cx, cy - 20), "BillionAire's",
              font=_font(82, bold=True), anchor="mm", fill=gold)
    draw.text((cx, cy + 80), "_Thoughts",
              font=_font(64, bold=False), anchor="mm", fill=(200, 200, 200))

    path = TEMP_DIR / "frame_intro.png"
    img.save(str(path), "PNG")
    return path


def _main_frame(content_data: dict) -> Path:
    """
    22-second main content frame.
    Text block is positioned in the upper-centre third of the screen —
    leaving the bottom third clear for YouTube's UI (like/comment/share buttons).
    """
    mood    = content_data.get("mood", "wealth_fact")
    content = content_data["content"]
    theme   = VISUAL_THEMES.get(mood, VISUAL_THEMES["wealth_fact"])

    img  = _make_gradient(theme)
    draw = ImageDraw.Draw(img)

    cx      = VIDEO_WIDTH  // 2
    accent  = theme["accent_color"]
    txt_col = theme["text_color"]
    glow    = theme["glow_color"]

    # Top + bottom accent bars
    draw.rectangle([0, 0, VIDEO_WIDTH, 8], fill=accent)
    draw.rectangle([0, VIDEO_HEIGHT - 8, VIDEO_WIDTH, VIDEO_HEIGHT], fill=accent)

    # Channel watermark — top
    draw.text((cx, 60), f"BillionAire's _Thoughts",
              font=_font(38, bold=False), anchor="mm", fill=accent)

    # Mood label
    draw.text((cx, 120), theme["label"],
              font=_font(32, bold=True), anchor="mm", fill=accent)

    # Decorative top divider
    draw.line([(60, 155), (VIDEO_WIDTH - 60, 155)], fill=accent, width=2)

    # ── Main content text ──────────────────────────────────────
    # Positioned starting at 30% from top — leaves bottom 35% for YouTube UI
    content_font = _font(72, bold=True)
    padding_x    = 70
    max_px       = VIDEO_WIDTH - padding_x * 2
    lines        = _wrap(content, content_font, max_px, draw)
    line_h       = 105
    block_h      = len(lines) * line_h

    # Start at 30% from top, not dead centre — avoids YouTube button overlap
    start_y = int(VIDEO_HEIGHT * 0.30)

    for i, line in enumerate(lines):
        y = start_y + i * line_h

        # Soft glow layer
        for offset in [(-3, -3), (3, -3), (-3, 3), (3, 3), (0, -4), (0, 4)]:
            draw.text(
                (cx + offset[0], y + offset[1]), line,
                font=content_font, anchor="mm",
                fill=(*glow, 160) if len(glow) == 3 else glow,
            )

        # Main text
        draw.text((cx, y), line,
                  font=content_font, anchor="mm", fill=txt_col)

    # Divider below text
    sep_y = start_y + block_h + 45
    draw.line([(60, sep_y), (VIDEO_WIDTH - 60, sep_y)], fill=accent, width=2)

    # Bottom CTA — fixed at bottom, above YouTube UI zone
    draw.text((cx, VIDEO_HEIGHT - 130),
              "Follow for daily wealth secrets",
              font=_font(40, bold=False), anchor="mm", fill=(160, 160, 160))
    try:
        draw.text((cx + 310, VIDEO_HEIGHT - 130), "💰",
                  font=_emoji_font(42), anchor="mm", fill=accent)
    except Exception:
        pass

    path = TEMP_DIR / "frame_main.png"
    img.save(str(path), "PNG")
    return path


def _outro_frame() -> Path:
    """3-second outro — follow CTA."""
    img  = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    for y in range(VIDEO_HEIGHT):
        t = y / VIDEO_HEIGHT
        r = int(22 * (1 - t))
        g = int(16 * (1 - t))
        draw.line([(0, y), (VIDEO_WIDTH, y)], fill=(r, g, 0))

    cx   = VIDEO_WIDTH  // 2
    cy   = VIDEO_HEIGHT // 2
    gold = (255, 210, 0)

    draw.text((cx, cy - 180), "Follow for more",
              font=_font(68, bold=True), anchor="mm", fill=(255, 255, 255))
    try:
        draw.text((cx, cy - 40), "💰",
                  font=_emoji_font(130), anchor="mm", fill=gold)
    except Exception:
        draw.text((cx, cy - 40), "$",
                  font=_font(110), anchor="mm", fill=gold)

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
            "GitHub Actions: add this to upload.yml:\n"
            "  - run: sudo apt-get install -y ffmpeg\n"
            "Windows: winget install ffmpeg"
        )


def _image_to_clip(img_path: Path, duration: float, out_path: Path,
                   zoom: bool = False) -> Path:
    """
    Convert a PNG image into a video clip.
    Zoom uses a lightweight scale-first approach to avoid memory issues
    on GitHub Actions free tier.
    """
    _check_ffmpeg()

    if zoom:
        # Scale to full res FIRST, then apply gentle zoom — much lighter on RAM
        vf = (
            f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT},"
            f"zoompan=z='min(zoom+0.0005,1.12)':d=1:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:fps={VIDEO_FPS},"
            f"setsar=1"
        )
    else:
        vf = f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT},setsar=1"

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(img_path),
        "-vf", vf,
        "-t", str(duration),
        "-c:v", "libx264",
        "-preset", "fast",       # faster encoding, same quality
        "-crf", "23",             # quality level (18=best, 28=worst, 23=default)
        "-pix_fmt", "yuv420p",
        "-r", str(VIDEO_FPS),
        str(out_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg clip error:\n{result.stderr[-800:]}")
    return out_path


def _pick_music() -> Path:
    """Return least-recently-used music track from music/ folder."""
    exts   = {".mp3", ".wav", ".m4a", ".aac", ".ogg"}
    tracks = [p for p in MUSIC_DIR.iterdir() if p.suffix.lower() in exts]
    if not tracks:
        raise FileNotFoundError(
            f"No music files found in {MUSIC_DIR}/\n"
            "Add MP3 files to the music/ folder and commit them to GitHub."
        )
    return min(tracks, key=lambda p: p.stat().st_atime)


# ── Main entry point ──────────────────────────────────────────

def create_video(content_data: dict) -> Path:
    """
    Assemble the complete video:
      Intro (2s) + Main (22s) + Outro (3s) + trap music
    Returns Path to the final MP4.
    """
    _check_ffmpeg()
    ts = int(time.time())
    log.info("Creating video frames...")

    intro_png = _intro_frame()
    main_png  = _main_frame(content_data)
    outro_png = _outro_frame()

    log.info("Rendering clips...")
    intro_mp4  = TEMP_DIR / f"clip_intro_{ts}.mp4"
    main_mp4   = TEMP_DIR / f"clip_main_{ts}.mp4"
    outro_mp4  = TEMP_DIR / f"clip_outro_{ts}.mp4"
    concat_mp4 = TEMP_DIR / f"concat_{ts}.mp4"
    concat_txt = TEMP_DIR / f"concat_{ts}.txt"
    final_mp4  = TEMP_DIR / f"video_{ts}.mp4"

    _image_to_clip(intro_png, float(INTRO_DURATION_SECONDS), intro_mp4, zoom=False)
    _image_to_clip(main_png,  float(MAIN_DURATION_SECONDS),  main_mp4,  zoom=True)
    _image_to_clip(outro_png, float(OUTRO_DURATION_SECONDS), outro_mp4, zoom=False)

    log.info("Concatenating clips...")
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
        raise RuntimeError(f"FFmpeg concat error:\n{result.stderr[-600:]}")

    log.info("Adding music...")
    music      = _pick_music()
    total_dur  = INTRO_DURATION_SECONDS + MAIN_DURATION_SECONDS + OUTRO_DURATION_SECONDS
    fade_start = total_dur - 2

    result = subprocess.run([
        "ffmpeg", "-y",
        "-i", str(concat_mp4),
        "-stream_loop", "-1",
        "-i", str(music),
        "-map", "0:v",
        "-map", "1:a",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-af", f"volume=0.3,afade=t=out:st={fade_start}:d=2",
        "-t", str(total_dur),
        str(final_mp4),
    ], capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg music error:\n{result.stderr[-600:]}")

    for f in [intro_png, main_png, outro_png,
              intro_mp4, main_mp4, outro_mp4,
              concat_mp4, concat_txt]:
        try:
            f.unlink(missing_ok=True)
        except Exception:
            pass

    log.info(f"Video ready: {final_mp4.name}")
    return final_mp4
