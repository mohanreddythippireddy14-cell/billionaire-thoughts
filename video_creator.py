# video_creator.py
# ============================================================
# Creates the final video — new structure March 2026
#
# Video structure (27 seconds, NO intro):
#   ┌──────────────────────────────────────┐
#   │  Hook          (8s)  — open loop     │
#   │  Answer       (10s)  — brutal reveal │  ← Pexels HD background
#   │  Comment bait  (3s)  — question      │
#   │  Agree/disag.  (3s)  — CTA           │
#   │  Outro         (3s)  — follow CTA    │
#   └──────────────────────────────────────┘
#
# Key improvements:
#   - NO static intro (was killing retention in 0.5s)
#   - Pexels landscape HD → cropped to 9:16 (fixes 360p resolution bug)
#   - min_duration=25 on Pexels API (fixes 10s clip bug)
#   - Bold text slams in on frame 1 instantly
#   - Comment bait + agree/disagree frames added
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
    AGREE_DISAGREE_DURATION_SECONDS,
    CHANNEL_NAME, COMMENT_BAIT_DURATION_SECONDS,
    FONTS_DIR, HOOK_DURATION_SECONDS, ANSWER_DURATION_SECONDS,
    MAIN_DURATION_SECONDS, MUSIC_DIR,
    OUTRO_DURATION_SECONDS, TEMP_DIR, VIDEO_FPS,
    VIDEO_HEIGHT, VIDEO_WIDTH, VISUAL_THEMES,
)

log = logging.getLogger("VideoCreator")

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")

MOOD_QUERIES = {
    "dark_truth": [
        "dark silhouette man walking", "dark forest cinematic",
        "shadow dramatic night", "lone figure darkness",
        "dark rain storm dramatic", "night city shadow",
    ],
    "mindset": [
        "mountain peak dramatic", "dark stormy sky",
        "man standing cliff sunset", "dark ocean waves crashing",
        "silhouette warrior sunset", "dark clouds timelapse",
    ],
    "wealth_fact": [
        "city lights night aerial", "skyscraper night dramatic",
        "businessman walking city", "night skyline timelapse",
        "dark luxury interior", "office building night",
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
    for p in [
        Path("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"),
        Path("/usr/share/fonts/noto/NotoColorEmoji.ttf"),
        Path("/usr/share/fonts/truetype/noto-color-emoji/NotoColorEmoji.ttf"),
    ]:
        try:
            return ImageFont.truetype(str(p), size)
        except Exception:
            continue
    return _font(size)


# ── Pexels ────────────────────────────────────────────────────

def _fetch_pexels_video(mood: str) -> Path | None:
    """
    Fetch HD video from Pexels.
    Key fixes:
    - Searches landscape (always HD) then crops to 9:16 via FFmpeg
    - min_duration=25 ensures clip is long enough for 18s main section
    - Falls back to gradient if unavailable
    """
    if not PEXELS_API_KEY:
        log.warning("PEXELS_API_KEY not set — gradient fallback")
        return None

    query = random.choice(MOOD_QUERIES.get(mood, MOOD_QUERIES["dark_truth"]))

    try:
        log.info(f"Fetching Pexels video: '{query}'...")

        # Search landscape — always has HD files unlike portrait
        resp = requests.get(
            "https://api.pexels.com/videos/search",
            headers={"Authorization": PEXELS_API_KEY},
            params={
                "query":        query,
                "orientation":  "landscape",    # landscape = always HD available
                "size":         "large",         # large = HD quality
                "per_page":     20,
                "min_duration": 25,             # must be longer than our 18s main clip
            },
            timeout=20,
        )
        resp.raise_for_status()
        videos = resp.json().get("videos", [])

        if not videos:
            # Broader fallback search
            resp2 = requests.get(
                "https://api.pexels.com/videos/search",
                headers={"Authorization": PEXELS_API_KEY},
                params={
                    "query":        "dark dramatic night",
                    "orientation":  "landscape",
                    "per_page":     15,
                    "min_duration": 20,
                },
                timeout=20,
            )
            resp2.raise_for_status()
            videos = resp2.json().get("videos", [])

        if not videos:
            log.warning("No Pexels videos found — gradient fallback")
            return None

        video = random.choice(videos[:10])
        files = video.get("video_files", [])

        # Pick highest resolution file (landscape HD)
        hd_files = [f for f in files if f.get("quality") in ("hd", "uhd")]
        chosen   = (
            max(hd_files, key=lambda f: f.get("width", 0))
            if hd_files
            else max(files, key=lambda f: f.get("width", 0))
        )

        url = chosen.get("link", "")
        if not url:
            return None

        dest = TEMP_DIR / f"pexels_{video['id']}_{int(time.time())}.mp4"
        log.info(f"Downloading {video['id']} ({chosen.get('width')}x{chosen.get('height')})...")

        dl = requests.get(url, timeout=90, stream=True)
        dl.raise_for_status()
        with open(dest, "wb") as fh:
            for chunk in dl.iter_content(1024 * 512):
                fh.write(chunk)

        size_mb = dest.stat().st_size / 1_000_000
        log.info(f"Downloaded: {dest.name} ({size_mb:.1f} MB)")
        return dest

    except Exception as exc:
        log.warning(f"Pexels failed: {exc} — gradient fallback")
        return None


def _process_background(src: Path, duration: float, out: Path) -> Path:
    """
    Landscape HD → 9:16 crop → 1080×1920 scale → darken → trim.
    This is what fixes the 360p resolution bug.
    Landscape videos are always HD; we crop centre to get portrait.
    """
    _check_ffmpeg()
    # crop centre 9:16 from landscape, scale to exact 1080×1920, darken 50%
    vf = (
        "crop=ih*9/16:ih:(iw-ih*9/16)/2:0,"   # centre crop to 9:16
        f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT},"  # scale to exact size
        "setsar=1,"
        "colorchannelmixer=rr=0.50:gg=0.50:bb=0.50"  # darken 50%
    )
    cmd = [
        "ffmpeg", "-y", "-i", str(src),
        "-vf", vf,
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-pix_fmt", "yuv420p", "-r", str(VIDEO_FPS),
        "-an", str(out),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        raise RuntimeError(f"Background processing error:\n{r.stderr[-600:]}")
    return out


def _make_gradient_clip(theme: dict, duration: float, out: Path) -> Path:
    """Fallback: render gradient as static clip."""
    img  = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT))
    draw = ImageDraw.Draw(img)
    top, bot = theme["bg_top"], theme["bg_bottom"]
    for y in range(VIDEO_HEIGHT):
        t = y / VIDEO_HEIGHT
        draw.line([(0, y), (VIDEO_WIDTH, y)], fill=(
            int(top[0] + (bot[0] - top[0]) * t),
            int(top[1] + (bot[1] - top[1]) * t),
            int(top[2] + (bot[2] - top[2]) * t),
        ))
    tmp = TEMP_DIR / f"grad_{int(time.time())}.png"
    img.save(str(tmp), "PNG")
    _image_to_clip(tmp, duration, out)
    tmp.unlink(missing_ok=True)
    return out


# ── Text helpers ──────────────────────────────────────────────

def _wrap(text: str, font, max_px: int, draw: ImageDraw.Draw) -> list[str]:
    words, lines, cur = text.split(), [], []
    for word in words:
        test = " ".join(cur + [word])
        if draw.textbbox((0, 0), test, font=font)[2] <= max_px:
            cur.append(word)
        else:
            if cur:
                lines.append(" ".join(cur))
            cur = [word]
    if cur:
        lines.append(" ".join(cur))
    return lines


def _render_overlay(text: str, accent: tuple, font_size: int = 72,
                    center_y_pct: float = 0.45) -> Image.Image:
    """
    Render text as transparent RGBA overlay.
    Dark pill behind each line for readability on any background.
    """
    img  = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx   = VIDEO_WIDTH // 2

    # Watermark strip at top
    draw.rectangle([0, 0, VIDEO_WIDTH, 6], fill=(*accent, 220))
    draw.rectangle([0, 15, VIDEO_WIDTH, 85], fill=(0, 0, 0, 160))
    draw.text((cx, 50), "BillionAire's _Thoughts",
              font=_font(32, bold=False), anchor="mm",
              fill=(*accent, 230))

    # Main text
    font      = _font(font_size, bold=True)
    pad_x     = 65
    max_px    = VIDEO_WIDTH - pad_x * 2
    lines     = _wrap(text, font, max_px, draw)
    line_h    = int(font_size * 1.45)
    block_h   = len(lines) * line_h
    start_y   = int(VIDEO_HEIGHT * center_y_pct) - block_h // 2

    for i, line in enumerate(lines):
        y    = start_y + i * line_h
        bbox = draw.textbbox((cx, y), line, font=font, anchor="mm")
        # Dark pill
        draw.rectangle(
            [bbox[0] - 14, bbox[1] - 8, bbox[2] + 14, bbox[3] + 8],
            fill=(0, 0, 0, 180),
        )
        # Shadow
        for dx, dy in [(-2, 2), (2, 2), (-2, -2), (2, -2)]:
            draw.text((cx + dx, y + dy), line, font=font,
                      anchor="mm", fill=(0, 0, 0, 200))
        # Text — always white
        draw.text((cx, y), line, font=font,
                  anchor="mm", fill=(255, 255, 255, 255))

    # Bottom accent bar
    draw.rectangle([0, VIDEO_HEIGHT - 6, VIDEO_WIDTH, VIDEO_HEIGHT],
                   fill=(*accent, 220))
    return img


# ── Frame PNG creators ────────────────────────────────────────

def _hook_overlay(content_data: dict) -> Path:
    """Hook text overlay — large, centred high."""
    theme  = VISUAL_THEMES.get(content_data["mood"], VISUAL_THEMES["dark_truth"])
    accent = theme["accent_color"]
    img    = _render_overlay(content_data["hook"], accent,
                              font_size=78, center_y_pct=0.42)

    # Mood label
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 88, VIDEO_WIDTH, 134], fill=(0, 0, 0, 140))
    draw.text((VIDEO_WIDTH // 2, 111), theme["label"],
              font=_font(28, bold=True), anchor="mm",
              fill=(*accent, 220))

    p = TEMP_DIR / "overlay_hook.png"
    img.save(str(p), "PNG")
    return p


def _answer_overlay(content_data: dict) -> Path:
    """Answer text overlay — slightly smaller, same position."""
    theme  = VISUAL_THEMES.get(content_data["mood"], VISUAL_THEMES["dark_truth"])
    accent = theme["accent_color"]
    img    = _render_overlay(content_data["answer"], accent,
                              font_size=70, center_y_pct=0.44)
    p = TEMP_DIR / "overlay_answer.png"
    img.save(str(p), "PNG")
    return p


def _comment_bait_frame(content_data: dict) -> Path:
    """Comment question frame — centred, dark background."""
    theme  = VISUAL_THEMES.get(content_data["mood"], VISUAL_THEMES["dark_truth"])
    accent = theme["accent_color"]

    img  = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), (8, 8, 8))
    draw = ImageDraw.Draw(img)

    cx, cy = VIDEO_WIDTH // 2, VIDEO_HEIGHT // 2

    # Accent lines
    draw.line([(80, cy - 160), (VIDEO_WIDTH - 80, cy - 160)],
              fill=accent, width=3)
    draw.line([(80, cy + 160), (VIDEO_WIDTH - 80, cy + 160)],
              fill=accent, width=3)

    # Watermark
    draw.text((cx, 55), "BillionAire's _Thoughts",
              font=_font(32, bold=False), anchor="mm", fill=accent)

    # Question text
    font    = _font(68, bold=True)
    pad_x   = 80
    max_px  = VIDEO_WIDTH - pad_x * 2
    lines   = _wrap(content_data["comment_question"], font, max_px, draw)
    line_h  = 100
    block_h = len(lines) * line_h
    start_y = cy - block_h // 2

    for i, line in enumerate(lines):
        y = start_y + i * line_h
        # Shadow
        for dx, dy in [(-2, 2), (2, 2)]:
            draw.text((cx + dx, y + dy), line, font=font,
                      anchor="mm", fill=(0, 0, 0))
        draw.text((cx, y), line, font=font,
                  anchor="mm", fill=(255, 255, 255))

    p = TEMP_DIR / "frame_comment.png"
    img.save(str(p), "PNG")
    return p


def _agree_disagree_frame(content_data: dict) -> Path:
    """Agree/Disagree CTA frame."""
    theme  = VISUAL_THEMES.get(content_data["mood"], VISUAL_THEMES["dark_truth"])
    accent = theme["accent_color"]

    img  = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), (8, 8, 8))
    draw = ImageDraw.Draw(img)
    cx, cy = VIDEO_WIDTH // 2, VIDEO_HEIGHT // 2

    draw.line([(80, cy - 200), (VIDEO_WIDTH - 80, cy - 200)],
              fill=accent, width=3)
    draw.line([(80, cy + 100), (VIDEO_WIDTH - 80, cy + 100)],
              fill=accent, width=3)

    draw.text((cx, 55), "BillionAire's _Thoughts",
              font=_font(32, bold=False), anchor="mm", fill=accent)

    draw.text((cx, cy - 120), "Agree or disagree?",
              font=_font(62, bold=True), anchor="mm", fill=(255, 255, 255))
    draw.text((cx, cy - 20), "Drop it below",
              font=_font(54, bold=False), anchor="mm", fill=(200, 200, 200))

    # Down arrow indicator
    draw.text((cx, cy + 60), "↓",
              font=_font(80, bold=True), anchor="mm", fill=accent)

    p = TEMP_DIR / "frame_agree.png"
    img.save(str(p), "PNG")
    return p


def _outro_frame() -> Path:
    """Follow CTA outro."""
    img  = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    for y in range(VIDEO_HEIGHT):
        t = y / VIDEO_HEIGHT
        draw.line([(0, y), (VIDEO_WIDTH, y)],
                  fill=(int(22 * (1 - t)), int(16 * (1 - t)), 0))

    cx, cy = VIDEO_WIDTH // 2, VIDEO_HEIGHT // 2
    gold   = (255, 210, 0)

    draw.text((cx, cy - 160), "Follow for more",
              font=_font(68, bold=True), anchor="mm", fill=(255, 255, 255))
    try:
        draw.text((cx, cy - 30), "💰",
                  font=_emoji_font(120), anchor="mm", fill=gold)
    except Exception:
        draw.text((cx, cy - 30), "$", font=_font(110), anchor="mm", fill=gold)

    draw.text((cx, cy + 100), CHANNEL_NAME,
              font=_font(56, bold=True), anchor="mm", fill=gold)
    draw.text((cx, cy + 195), "New video every night",
              font=_font(40, bold=False), anchor="mm", fill=(160, 160, 160))

    p = TEMP_DIR / "frame_outro.png"
    img.save(str(p), "PNG")
    return p


# ── FFmpeg helpers ────────────────────────────────────────────

def _check_ffmpeg():
    if not shutil.which("ffmpeg"):
        raise EnvironmentError("FFmpeg not found!")


def _image_to_clip(img: Path, dur: float, out: Path) -> Path:
    """Static PNG → video clip."""
    _check_ffmpeg()
    r = subprocess.run([
        "ffmpeg", "-y", "-loop", "1", "-i", str(img),
        "-vf", f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT},setsar=1",
        "-t", str(dur),
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-pix_fmt", "yuv420p", "-r", str(VIDEO_FPS),
        str(out),
    ], capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        raise RuntimeError(f"Image clip error:\n{r.stderr[-500:]}")
    return out


def _overlay_on_clip(clip: Path, overlay: Path, out: Path) -> Path:
    """Composite RGBA PNG overlay on top of video clip."""
    _check_ffmpeg()
    r = subprocess.run([
        "ffmpeg", "-y",
        "-i", str(clip), "-i", str(overlay),
        "-filter_complex", "[0:v][1:v]overlay=0:0[v]",
        "-map", "[v]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-pix_fmt", "yuv420p", "-r", str(VIDEO_FPS),
        str(out),
    ], capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        raise RuntimeError(f"Overlay error:\n{r.stderr[-500:]}")
    return out


def _trim_clip(src: Path, start: float, duration: float, out: Path) -> Path:
    """Trim a segment from a video clip."""
    _check_ffmpeg()
    r = subprocess.run([
        "ffmpeg", "-y",
        "-ss", str(start), "-i", str(src),
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-pix_fmt", "yuv420p", "-r", str(VIDEO_FPS),
        "-an", str(out),
    ], capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(f"Trim error:\n{r.stderr[-500:]}")
    return out


def _pick_music() -> Path:
    exts   = {".mp3", ".wav", ".m4a", ".aac", ".ogg"}
    tracks = [p for p in MUSIC_DIR.iterdir() if p.suffix.lower() in exts]
    if not tracks:
        raise FileNotFoundError(f"No music in {MUSIC_DIR}/")
    return min(tracks, key=lambda p: p.stat().st_atime)


# ── Main entry point ──────────────────────────────────────────

def create_video(content_data: dict) -> Path:
    """
    Assemble 27-second video:
      Hook (8s) + Answer (10s) — Pexels HD background
      Comment bait (3s) + Agree/Disagree (3s) + Outro (3s) — static

    Returns Path to final MP4.
    """
    _check_ffmpeg()
    ts   = int(time.time())
    mood = content_data.get("mood", "dark_truth")
    log.info(f"Creating video | mood={mood} | audience={content_data.get('audience','us')}")

    # Temp paths
    pexels_raw  = None
    bg_full     = TEMP_DIR / f"bg_full_{ts}.mp4"
    bg_hook     = TEMP_DIR / f"bg_hook_{ts}.mp4"
    bg_answer   = TEMP_DIR / f"bg_answer_{ts}.mp4"
    hook_mp4    = TEMP_DIR / f"clip_hook_{ts}.mp4"
    answer_mp4  = TEMP_DIR / f"clip_answer_{ts}.mp4"
    comment_mp4 = TEMP_DIR / f"clip_comment_{ts}.mp4"
    agree_mp4   = TEMP_DIR / f"clip_agree_{ts}.mp4"
    outro_mp4   = TEMP_DIR / f"clip_outro_{ts}.mp4"
    concat_mp4  = TEMP_DIR / f"concat_{ts}.mp4"
    concat_txt  = TEMP_DIR / f"concat_{ts}.txt"
    final_mp4   = TEMP_DIR / f"video_{ts}.mp4"
    combined_h  = TEMP_DIR / f"combined_hook_{ts}.png"
    combined_a  = TEMP_DIR / f"combined_ans_{ts}.png"

    try:
        theme = VISUAL_THEMES.get(mood, VISUAL_THEMES["dark_truth"])

        # 1. Render overlays and static frames
        log.info("Rendering overlays...")
        hook_overlay    = _hook_overlay(content_data)
        answer_overlay  = _answer_overlay(content_data)
        comment_png     = _comment_bait_frame(content_data)
        agree_png       = _agree_disagree_frame(content_data)
        outro_png       = _outro_frame()

        # 2. Fetch Pexels HD background
        log.info("Fetching Pexels background...")
        pexels_raw = _fetch_pexels_video(mood)

        if pexels_raw and pexels_raw.exists():
            # Process to 1080×1920 — landscape → centre crop → scale → darken
            _process_background(pexels_raw, float(MAIN_DURATION_SECONDS), bg_full)

            # Split background into hook (0-8s) and answer (8-18s) segments
            _trim_clip(bg_full, 0, float(HOOK_DURATION_SECONDS),   bg_hook)
            _trim_clip(bg_full, float(HOOK_DURATION_SECONDS),
                       float(ANSWER_DURATION_SECONDS), bg_answer)

            # Composite text on background
            _overlay_on_clip(bg_hook,   hook_overlay,   hook_mp4)
            _overlay_on_clip(bg_answer, answer_overlay, answer_mp4)

        else:
            # Gradient fallback
            log.info("Using gradient fallback...")
            _make_gradient_clip(theme, float(HOOK_DURATION_SECONDS),   bg_hook)
            _make_gradient_clip(theme, float(ANSWER_DURATION_SECONDS), bg_answer)

            overlay_h = Image.open(str(hook_overlay)).convert("RGBA")
            overlay_a = Image.open(str(answer_overlay)).convert("RGBA")
            grad_h    = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT))
            grad_a    = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT))

            # Draw gradients
            draw_h = ImageDraw.Draw(grad_h)
            draw_a = ImageDraw.Draw(grad_a)
            top, bot = theme["bg_top"], theme["bg_bottom"]
            for y in range(VIDEO_HEIGHT):
                t = y / VIDEO_HEIGHT
                c = (int(top[0]+(bot[0]-top[0])*t),
                     int(top[1]+(bot[1]-top[1])*t),
                     int(top[2]+(bot[2]-top[2])*t))
                draw_h.line([(0,y),(VIDEO_WIDTH,y)], fill=c)
                draw_a.line([(0,y),(VIDEO_WIDTH,y)], fill=c)

            Image.alpha_composite(grad_h.convert("RGBA"), overlay_h).convert("RGB").save(str(combined_h))
            Image.alpha_composite(grad_a.convert("RGBA"), overlay_a).convert("RGB").save(str(combined_a))
            _image_to_clip(combined_h, float(HOOK_DURATION_SECONDS),   hook_mp4)
            _image_to_clip(combined_a, float(ANSWER_DURATION_SECONDS), answer_mp4)

        # 3. Static clips
        log.info("Rendering static clips...")
        _image_to_clip(comment_png, float(COMMENT_BAIT_DURATION_SECONDS),   comment_mp4)
        _image_to_clip(agree_png,   float(AGREE_DISAGREE_DURATION_SECONDS), agree_mp4)
        _image_to_clip(outro_png,   float(OUTRO_DURATION_SECONDS),          outro_mp4)

        # 4. Concatenate all 5 clips
        log.info("Concatenating...")
        concat_txt.write_text(
            f"file '{hook_mp4.resolve()}'\n"
            f"file '{answer_mp4.resolve()}'\n"
            f"file '{comment_mp4.resolve()}'\n"
            f"file '{agree_mp4.resolve()}'\n"
            f"file '{outro_mp4.resolve()}'\n"
        )
        r = subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_txt), "-c", "copy", str(concat_mp4),
        ], capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            raise RuntimeError(f"Concat error:\n{r.stderr[-500:]}")

        # 5. Add music
        log.info("Adding music...")
        music     = _pick_music()
        total_dur = (HOOK_DURATION_SECONDS + ANSWER_DURATION_SECONDS +
                     COMMENT_BAIT_DURATION_SECONDS + AGREE_DISAGREE_DURATION_SECONDS +
                     OUTRO_DURATION_SECONDS)
        fade_start = total_dur - 2

        r = subprocess.run([
            "ffmpeg", "-y",
            "-i", str(concat_mp4),
            "-stream_loop", "-1", "-i", str(music),
            "-map", "0:v", "-map", "1:a",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-af", f"volume=0.28,afade=t=out:st={fade_start}:d=2",
            "-t", str(total_dur),
            str(final_mp4),
        ], capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            raise RuntimeError(f"Music error:\n{r.stderr[-500:]}")

        size_mb = final_mp4.stat().st_size / 1_000_000
        log.info(f"Video ready: {final_mp4.name} ({size_mb:.1f} MB)")
        return final_mp4

    finally:
        for f in [bg_full, bg_hook, bg_answer,
                  hook_mp4, answer_mp4, comment_mp4, agree_mp4, outro_mp4,
                  concat_mp4, concat_txt, combined_h, combined_a,
                  hook_overlay, answer_overlay, comment_png, agree_png, outro_png]:
            try:
                Path(f).unlink(missing_ok=True)
            except Exception:
                pass
        if pexels_raw:
            try:
                pexels_raw.unlink(missing_ok=True)
            except Exception:
                pass
