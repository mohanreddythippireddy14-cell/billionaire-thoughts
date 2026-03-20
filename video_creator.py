# video_creator.py
# ============================================================
# Creates the final video using Pillow (images) + FFmpeg (video)
#
# Video structure:
#   ┌─────────────────────────────────────┐
#   │  Intro     (2s)  — channel branding │
#   │  Main     (22s)  — finance content  │  ← Ken Burns zoom effect
#   │  Outro     (3s)  — follow CTA       │
#   └─────────────────────────────────────┘
#   Total: ~27 seconds — perfect for YouTube Shorts
#
# Format: 1080×1920 (9:16 portrait), 30fps, H.264
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


# ── Fonts ────────────────────────────────────────────────────

def _font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    """
    Load font. Priority:
    1. Montserrat (committed to fonts/ folder after running setup_fonts.py)
    2. DejaVu Sans (always available on GitHub Actions Ubuntu runner)
    3. PIL fallback (ugly but never crashes)
    """
    candidates = [
        FONTS_DIR / ("Montserrat-Bold.ttf" if bold else "Montserrat-Regular.ttf"),
        FONTS_DIR / "Montserrat-Bold.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ]
    for p in candidates:
        try:
            return ImageFont.truetype(str(p), size)
        except Exception:
            continue
    log.warning("No TTF font found — falling back to PIL default (lower quality)")
    return ImageFont.load_default()


# ── Background ───────────────────────────────────────────────

def _make_gradient(theme: dict) -> Image.Image:
    """
    Create a cinematic dark gradient background.
    Top colour → bottom colour, blended line by line.
    """
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


# ── Text helpers ─────────────────────────────────────────────

def _wrap(text: str, font, max_px: int, draw: ImageDraw.Draw) -> list[str]:
    """Word-wrap text to fit within max_px width. Returns list of lines."""
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
               font, glow_color: tuple, radius: int = 10):
    """Draw soft glow behind text by rendering it multiple times with offset."""
    for r in range(radius, 0, -2):
        # Opacity decreases as radius increases
        opacity = int(120 * (1 - r / radius))
        color_with_alpha = (*glow_color, opacity) if False else glow_color
        for dx in [-r, 0, r]:
            for dy in [-r, 0, r]:
                draw.text(
                    (x + dx, y + dy), text,
                    font=font, anchor="mm", fill=color_with_alpha
                )


# ── Frame creators ───────────────────────────────────────────

def _intro_frame() -> Path:
    """2-second branded intro: gold logo + channel name on black."""
    img  = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Subtle dark gold gradient
    for y in range(VIDEO_HEIGHT):
        t = y / VIDEO_HEIGHT
        r = int(22 * (1 - t))
        g = int(16 * (1 - t))
        draw.line([(0, y), (VIDEO_WIDTH, y)], fill=(r, g, 0))

    cx = VIDEO_WIDTH  // 2
    cy = VIDEO_HEIGHT // 2
    gold = (255, 210, 0)

    # Top + bottom gold lines
    draw.line([(80, cy - 130), (VIDEO_WIDTH - 80, cy - 130)], fill=gold, width=2)
    draw.line([(80, cy + 130), (VIDEO_WIDTH - 80, cy + 130)], fill=gold, width=2)

    # Money bag emoji (rendered as text — works on Ubuntu runner)
    draw.text((cx, cy - 180), "💰", font=_font(110), anchor="mm", fill=gold)

    # Channel name
    draw.text((cx, cy - 30), "BillionAire's", font=_font(76), anchor="mm", fill=gold)
    draw.text((cx, cy + 65), "_Thoughts 😎",  font=_font(58, bold=False),
              anchor="mm", fill=(200, 200, 200))

    path = TEMP_DIR / "frame_intro.png"
    img.save(str(path), "PNG")
    return path


def _main_frame(content_data: dict) -> Path:
    """22-second main content frame with the finance insight."""
    mood    = content_data.get("mood", "wealth_fact")
    content = content_data["content"]
    theme   = VISUAL_THEMES.get(mood, VISUAL_THEMES["wealth_fact"])

    img  = _make_gradient(theme)
    draw = ImageDraw.Draw(img)

    cx      = VIDEO_WIDTH  // 2
    accent  = theme["accent_color"]
    glow    = theme["glow_color"]
    txt_col = theme["text_color"]

    # Top + bottom accent bars
    draw.rectangle([0, 0, VIDEO_WIDTH, 7],                      fill=accent)
    draw.rectangle([0, VIDEO_HEIGHT - 7, VIDEO_WIDTH, VIDEO_HEIGHT], fill=accent)

    # Channel watermark at top
    draw.text((cx, 55), f"💰 {CHANNEL_NAME}",
              font=_font(36, bold=False), anchor="mm", fill=accent)

    # Mood label (e.g. "WEALTH FACT", "DARK TRUTH")
    draw.text((cx, 112), theme["label"],
              font=_font(30, bold=True), anchor="mm", fill=accent)

    # ── Main content text ──────────────────────────────────────
    content_font = _font(66, bold=True)
    padding_x    = 90
    max_px       = VIDEO_WIDTH - padding_x * 2
    lines        = _wrap(content, content_font, max_px, draw)
    line_h       = 95
    block_h      = len(lines) * line_h
    start_y      = (VIDEO_HEIGHT - block_h) // 2

    for i, line in enumerate(lines):
        y = start_y + i * line_h
        _draw_glow(draw, line, cx, y, content_font, glow, radius=14)
        draw.text((cx, y), line, font=content_font, anchor="mm", fill=txt_col)

    # Accent line below text block
    sep_y = start_y + block_h + 35
    draw.line([(80, sep_y), (VIDEO_WIDTH - 80, sep_y)], fill=accent, width=2)

    # Bottom CTA
    draw.text((cx, VIDEO_HEIGHT - 95),
              "Follow for daily wealth secrets 💰",
              font=_font(38, bold=False), anchor="mm", fill=(160, 160, 160))

    path = TEMP_DIR / "frame_main.png"
    img.save(str(path), "PNG")
    return path


def _outro_frame() -> Path:
    """3-second outro: follow CTA + channel name."""
    img  = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Subtle warm gradient
    for y in range(VIDEO_HEIGHT):
        t = y / VIDEO_HEIGHT
        r = int(22 * (1 - t))
        g = int(16 * (1 - t))
        draw.line([(0, y), (VIDEO_WIDTH, y)], fill=(r, g, 0))

    cx = VIDEO_WIDTH  // 2
    cy = VIDEO_HEIGHT // 2
    gold = (255, 210, 0)

    draw.text((cx, cy - 160), "Follow for more",
              font=_font(62, bold=True), anchor="mm", fill=(255, 255, 255))
    draw.text((cx, cy - 40),  "💰",
              font=_font(110),           anchor="mm", fill=gold)
    draw.text((cx, cy + 100), CHANNEL_NAME,
              font=_font(52, bold=True),  anchor="mm", fill=gold)
    draw.text((cx, cy + 185), "New video every evening 🔔",
              font=_font(38, bold=False), anchor="mm", fill=(160, 160, 160))

    path = TEMP_DIR / "frame_outro.png"
    img.save(str(path), "PNG")
    return path


# ── FFmpeg helpers ────────────────────────────────────────────

def _check_ffmpeg():
    if not shutil.which("ffmpeg"):
        raise EnvironmentError(
            "FFmpeg not found!\n"
            "GitHub Actions: make sure your workflow has:\n"
            "  - run: sudo apt-get install -y ffmpeg\n"
            "Windows local test: winget install ffmpeg"
        )


def _image_to_clip(img_path: Path, duration: float, out_path: Path,
                   zoom: bool = False) -> Path:
    """
    Convert a PNG image into a video clip of the given duration.
    If zoom=True, adds a subtle Ken Burns zoom-in effect.
    """
    _check_ffmpeg()

    if zoom:
        # Slow zoom-in over the full duration — looks professional
        total_frames = int(duration * VIDEO_FPS)
        vf = (
            f"zoompan=z='min(zoom+0.0008,1.25)':d={total_frames}:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:fps={VIDEO_FPS},"
            f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT},setsar=1"
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
        "-pix_fmt", "yuv420p",
        "-r", str(VIDEO_FPS),
        str(out_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg clip error:\n{result.stderr[-600:]}")
    return out_path


def _pick_music() -> Path:
    """Return least-recently-used music track from music/ folder."""
    exts   = {".mp3", ".wav", ".m4a", ".aac", ".ogg"}
    tracks = [p for p in MUSIC_DIR.iterdir() if p.suffix.lower() in exts]
    if not tracks:
        raise FileNotFoundError(
            f"No music files found in {MUSIC_DIR}/\n"
            "Run: python setup_music.py\n"
            "Or manually add MP3 files to the music/ folder."
        )
    return min(tracks, key=lambda p: p.stat().st_atime)


# ── Main entry point ──────────────────────────────────────────

def create_video(content_data: dict) -> Path:
    """
    Assemble the complete video:
      Intro clip  (2s)
      Main clip  (22s)  ← Ken Burns zoom
      Outro clip  (3s)
      + trap music mixed in, fades out last 2 seconds

    Returns Path to the final MP4 file.
    """
    _check_ffmpeg()
    ts = int(time.time())
    log.info("Creating video frames...")

    # 1. Render PNG frames
    intro_png = _intro_frame()
    main_png  = _main_frame(content_data)
    outro_png = _outro_frame()

    # 2. Convert each frame to a video clip
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

    # 3. Concatenate clips
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

    # 4. Mix in music (looped, volume at 30%, fade-out last 2s)
    log.info("Adding music...")
    music      = _pick_music()
    total_dur  = INTRO_DURATION_SECONDS + MAIN_DURATION_SECONDS + OUTRO_DURATION_SECONDS
    fade_start = total_dur - 2

    result = subprocess.run([
        "ffmpeg", "-y",
        "-i", str(concat_mp4),
        "-stream_loop", "-1",     # loop music if shorter than video
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

    # 5. Clean up temp files
    for f in [intro_png, main_png, outro_png,
              intro_mp4, main_mp4, outro_mp4,
              concat_mp4, concat_txt]:
        try:
            f.unlink(missing_ok=True)
        except Exception:
            pass

    log.info(f"Video ready: {final_mp4.name}")
    return final_mp4
