# video_creator.py
# ============================================================
# Creates 15-second Shorts — March 2026
#
# Structure:
#   Hook   (5s) — bold text slams in on Pexels background
#   Answer (7s) — revelation text, same background continues
#   Outro  (3s) — follow CTA on gold gradient
#   Total: 15 seconds
#
# Why 15s:
#   Higher completion rate → algorithm pushes harder
#   Viewer re-watches → counts as multiple views
#   Forces tighter writing → better content
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
    ANSWER_DURATION_SECONDS, CHANNEL_NAME,
    FONTS_DIR, HOOK_DURATION_SECONDS,
    MAIN_DURATION_SECONDS, MUSIC_DIR,
    OUTRO_DURATION_SECONDS, TEMP_DIR, VIDEO_FPS,
    VIDEO_HEIGHT, VIDEO_WIDTH, VISUAL_THEMES,
)

log = logging.getLogger("VideoCreator")

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")
MAX_PEXELS_MB  = 80
SIZE_STR       = f"{VIDEO_WIDTH}x{VIDEO_HEIGHT}"

MOOD_QUERIES = {
    "dark_truth": [
        "dark silhouette man walking", "dark forest cinematic",
        "lone figure darkness", "shadow dramatic night",
        "dark rain storm city", "night city aerial dark",
    ],
    "mindset": [
        "mountain peak dramatic clouds", "dark stormy sky",
        "man standing cliff", "dark ocean waves",
        "silhouette sunset dramatic", "dark clouds moving",
    ],
    "wealth_fact": [
        "city lights night aerial", "skyscraper night",
        "businessman walking night", "night skyline timelapse",
        "dark office building", "luxury night city",
    ],
}


# ── Fonts ─────────────────────────────────────────────────────

def _font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    for p in [
        FONTS_DIR / ("Montserrat-Bold.ttf" if bold else "Montserrat-Regular.ttf"),
        FONTS_DIR / "Montserrat-Bold.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ]:
        try:
            return ImageFont.truetype(str(p), size)
        except Exception:
            continue
    return ImageFont.load_default()


# ── Pexels ────────────────────────────────────────────────────

def _fetch_pexels_video(mood: str) -> Path | None:
    """Fetch HD landscape video. Cap at 80MB. Falls back to gradient."""
    if not PEXELS_API_KEY:
        log.warning("PEXELS_API_KEY not set — gradient fallback")
        return None

    query = random.choice(MOOD_QUERIES.get(mood, MOOD_QUERIES["dark_truth"]))
    try:
        log.info(f"Pexels: '{query}'...")
        resp = requests.get(
            "https://api.pexels.com/videos/search",
            headers={"Authorization": PEXELS_API_KEY},
            params={"query": query, "orientation": "landscape",
                    "size": "large", "per_page": 20, "min_duration": 20},
            timeout=20,
        )
        resp.raise_for_status()
        videos = resp.json().get("videos", [])

        if not videos:
            resp2 = requests.get(
                "https://api.pexels.com/videos/search",
                headers={"Authorization": PEXELS_API_KEY},
                params={"query": "dark dramatic night", "orientation": "landscape",
                        "per_page": 15, "min_duration": 15},
                timeout=20,
            )
            resp2.raise_for_status()
            videos = resp2.json().get("videos", [])

        if not videos:
            return None

        video = random.choice(videos[:10])
        files = video.get("video_files", [])
        hd    = [f for f in files if f.get("quality") == "hd" and f.get("width", 9999) <= 1920]
        if not hd:
            hd = [f for f in files if f.get("quality") == "hd"]
        if not hd:
            hd = files

        hd.sort(key=lambda f: f.get("width", 0), reverse=True)
        url = hd[0].get("link", "") if hd else ""
        if not url:
            return None

        dest       = TEMP_DIR / f"pexels_{video['id']}_{int(time.time())}.mp4"
        downloaded = 0
        max_bytes  = MAX_PEXELS_MB * 1024 * 1024
        dl         = requests.get(url, timeout=90, stream=True)
        dl.raise_for_status()
        with open(dest, "wb") as fh:
            for chunk in dl.iter_content(1024 * 512):
                fh.write(chunk)
                downloaded += len(chunk)
                if downloaded > max_bytes:
                    break

        log.info(f"Downloaded: {dest.stat().st_size // 1024 // 1024:.0f}MB")
        return dest

    except Exception as exc:
        log.warning(f"Pexels failed: {exc} — gradient fallback")
        return None


def _process_bg(src: Path, duration: float, out: Path) -> Path:
    """Landscape → centre crop 9:16 → scale 1080×1920 → darken 45%."""
    _check_ffmpeg()
    vf = (
        "crop=ih*9/16:ih:(iw-ih*9/16)/2:0,"
        f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=disable,"
        "setsar=1,"
        "colorchannelmixer=rr=0.45:gg=0.45:bb=0.45"
    )
    r = subprocess.run([
        "ffmpeg", "-y", "-i", str(src),
        "-vf", vf, "-s", SIZE_STR,
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-pix_fmt", "yuv420p", "-r", str(VIDEO_FPS), "-an", str(out),
    ], capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(f"BG error:\n{r.stderr[-400:]}")
    return out


def _make_gradient(theme: dict) -> Image.Image:
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
    return img


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


def _render_overlay(text: str, accent: tuple, label: str,
                    font_size: int = 82,
                    center_y_pct: float = 0.44) -> Image.Image:
    """
    RGBA transparent overlay at 1080×1920.
    Text is always white, centered, with dark pill for readability.
    """
    img  = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx   = VIDEO_WIDTH // 2

    # Top accent bar
    draw.rectangle([0, 0, VIDEO_WIDTH, 6], fill=(*accent, 235))

    # Watermark
    draw.rectangle([0, 10, VIDEO_WIDTH, 85], fill=(0, 0, 0, 180))
    draw.text((cx, 47), "BillionAire's _Thoughts",
              font=_font(34, bold=False), anchor="mm",
              fill=(*accent, 240))

    # Mood label
    draw.rectangle([0, 85, VIDEO_WIDTH, 132], fill=(0, 0, 0, 150))
    draw.text((cx, 108), label,
              font=_font(28, bold=True), anchor="mm",
              fill=(*accent, 225))

    draw.line([(60, 137), (VIDEO_WIDTH - 60, 137)],
              fill=(*accent, 160), width=2)

    # Main text
    font    = _font(font_size, bold=True)
    pad_x   = 60
    max_px  = VIDEO_WIDTH - pad_x * 2
    lines   = _wrap(text, font, max_px, draw)
    line_h  = int(font_size * 1.38)
    block_h = len(lines) * line_h
    start_y = int(VIDEO_HEIGHT * center_y_pct) - block_h // 2

    for i, line in enumerate(lines):
        y    = start_y + i * line_h
        bbox = draw.textbbox((cx, y), line, font=font, anchor="mm")
        # Dark pill
        draw.rectangle(
            [bbox[0] - 18, bbox[1] - 12, bbox[2] + 18, bbox[3] + 12],
            fill=(0, 0, 0, 190),
        )
        # Shadow
        for dx, dy in [(-2, 3), (2, 3), (-2, -2), (2, -2)]:
            draw.text((cx + dx, y + dy), line, font=font,
                      anchor="mm", fill=(0, 0, 0, 220))
        # Text
        draw.text((cx, y), line, font=font,
                  anchor="mm", fill=(255, 255, 255, 255))

    # Bottom accent
    draw.rectangle([0, VIDEO_HEIGHT - 6, VIDEO_WIDTH, VIDEO_HEIGHT],
                   fill=(*accent, 235))
    return img


def _hook_overlay(content_data: dict) -> Path:
    theme = VISUAL_THEMES.get(content_data["mood"], VISUAL_THEMES["dark_truth"])
    img   = _render_overlay(
        content_data["hook"],
        theme["accent_color"], theme["label"],
        font_size=88, center_y_pct=0.42,
    )
    p = TEMP_DIR / "overlay_hook.png"
    img.save(str(p), "PNG")
    return p


def _answer_overlay(content_data: dict) -> Path:
    theme = VISUAL_THEMES.get(content_data["mood"], VISUAL_THEMES["dark_truth"])
    img   = _render_overlay(
        content_data["answer"],
        theme["accent_color"], theme["label"],
        font_size=74, center_y_pct=0.45,
    )
    p = TEMP_DIR / "overlay_answer.png"
    img.save(str(p), "PNG")
    return p


def _outro_frame() -> Path:
    img  = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    for y in range(VIDEO_HEIGHT):
        t = y / VIDEO_HEIGHT
        draw.line([(0, y), (VIDEO_WIDTH, y)],
                  fill=(int(22 * (1-t)), int(16 * (1-t)), 0))

    cx, cy = VIDEO_WIDTH // 2, VIDEO_HEIGHT // 2
    gold   = (255, 210, 0)

    draw.text((cx, cy - 155), "Follow for more",
              font=_font(76, bold=True), anchor="mm", fill=(255, 255, 255))

    # Gold coin — circle with $ text, always renders
    draw.ellipse([cx-65, cy-50, cx+65, cy+80],
                 fill=gold, outline=(180, 140, 0), width=4)
    draw.text((cx, cy+15), "$",
              font=_font(70, bold=True), anchor="mm", fill=(0, 0, 0))

    draw.text((cx, cy + 120), CHANNEL_NAME,
              font=_font(56, bold=True), anchor="mm", fill=gold)
    draw.text((cx, cy + 205), "New video every night",
              font=_font(42, bold=False), anchor="mm", fill=(160, 160, 160))

    p = TEMP_DIR / "frame_outro.png"
    img.save(str(p), "PNG")
    return p


# ── FFmpeg ────────────────────────────────────────────────────

def _check_ffmpeg():
    if not shutil.which("ffmpeg"):
        raise EnvironmentError("FFmpeg not found!")


def _image_to_clip(img: Path, dur: float, out: Path) -> Path:
    _check_ffmpeg()
    r = subprocess.run([
        "ffmpeg", "-y", "-loop", "1", "-i", str(img),
        "-vf", f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=disable,setsar=1",
        "-s", SIZE_STR, "-t", str(dur),
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-pix_fmt", "yuv420p", "-r", str(VIDEO_FPS),
        str(out),
    ], capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(f"Image clip error:\n{r.stderr[-400:]}")
    return out


def _overlay_on_clip(clip: Path, overlay: Path, out: Path) -> Path:
    _check_ffmpeg()
    r = subprocess.run([
        "ffmpeg", "-y",
        "-i", str(clip), "-i", str(overlay),
        "-filter_complex",
        f"[0:v]scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=disable,setsar=1[bg];"
        f"[1:v]scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=disable[fg];"
        "[bg][fg]overlay=0:0[v]",
        "-map", "[v]",
        "-s", SIZE_STR,
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-pix_fmt", "yuv420p", "-r", str(VIDEO_FPS),
        str(out),
    ], capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(f"Overlay error:\n{r.stderr[-400:]}")
    return out


def _trim_clip(src: Path, start: float, dur: float, out: Path) -> Path:
    _check_ffmpeg()
    r = subprocess.run([
        "ffmpeg", "-y", "-ss", str(start), "-i", str(src),
        "-t", str(dur), "-s", SIZE_STR,
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-pix_fmt", "yuv420p", "-r", str(VIDEO_FPS), "-an", str(out),
    ], capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(f"Trim error:\n{r.stderr[-400:]}")
    return out


def _pick_music() -> Path:
    exts   = {".mp3", ".wav", ".m4a", ".aac", ".ogg"}
    tracks = [p for p in MUSIC_DIR.iterdir() if p.suffix.lower() in exts]
    if not tracks:
        raise FileNotFoundError(f"No music in {MUSIC_DIR}/")
    return min(tracks, key=lambda p: p.stat().st_atime)


# ── Main ──────────────────────────────────────────────────────

def create_video(content_data: dict) -> Path:
    """
    15-second video:
      Hook (5s) + Answer (7s) — Pexels HD or gradient
      Outro (3s) — gold gradient
    All output at 1080×1920.
    """
    _check_ffmpeg()
    ts   = int(time.time())
    mood = content_data.get("mood", "dark_truth")
    log.info(f"Creating 15s video | mood={mood} | audience={content_data.get('audience','us')}")

    pexels_raw = None
    bg_full    = TEMP_DIR / f"bg_full_{ts}.mp4"
    bg_hook    = TEMP_DIR / f"bg_hook_{ts}.mp4"
    bg_answer  = TEMP_DIR / f"bg_ans_{ts}.mp4"
    hook_mp4   = TEMP_DIR / f"clip_hook_{ts}.mp4"
    answer_mp4 = TEMP_DIR / f"clip_ans_{ts}.mp4"
    outro_mp4  = TEMP_DIR / f"clip_outro_{ts}.mp4"
    concat_mp4 = TEMP_DIR / f"concat_{ts}.mp4"
    concat_txt = TEMP_DIR / f"concat_{ts}.txt"
    final_mp4  = TEMP_DIR / f"video_{ts}.mp4"
    comb_h     = TEMP_DIR / f"comb_hook_{ts}.png"
    comb_a     = TEMP_DIR / f"comb_ans_{ts}.png"

    try:
        theme = VISUAL_THEMES.get(mood, VISUAL_THEMES["dark_truth"])

        # 1. Render overlays
        log.info("Rendering overlays...")
        hook_ov  = _hook_overlay(content_data)
        ans_ov   = _answer_overlay(content_data)
        outro_png = _outro_frame()

        # 2. Fetch Pexels background
        pexels_raw = _fetch_pexels_video(mood)

        if pexels_raw and pexels_raw.exists():
            log.info("Processing Pexels background...")
            _process_bg(pexels_raw, float(MAIN_DURATION_SECONDS), bg_full)
            _trim_clip(bg_full, 0.0, float(HOOK_DURATION_SECONDS), bg_hook)
            _trim_clip(bg_full, float(HOOK_DURATION_SECONDS),
                       float(ANSWER_DURATION_SECONDS), bg_answer)
            _overlay_on_clip(bg_hook,   hook_ov, hook_mp4)
            _overlay_on_clip(bg_answer, ans_ov,  answer_mp4)
        else:
            log.info("Gradient fallback...")
            for ov_path, dur, out, comb in [
                (hook_ov,  HOOK_DURATION_SECONDS,   hook_mp4,   comb_h),
                (ans_ov,   ANSWER_DURATION_SECONDS, answer_mp4, comb_a),
            ]:
                grad = _make_gradient(theme)
                ov   = Image.open(str(ov_path)).convert("RGBA")
                Image.alpha_composite(
                    grad.convert("RGBA"), ov
                ).convert("RGB").save(str(comb), "PNG")
                _image_to_clip(comb, float(dur), out)

        # 3. Outro clip
        _image_to_clip(outro_png, float(OUTRO_DURATION_SECONDS), outro_mp4)

        # 4. Concatenate 3 clips
        log.info("Concatenating...")
        concat_txt.write_text(
            f"file '{hook_mp4.resolve()}'\n"
            f"file '{answer_mp4.resolve()}'\n"
            f"file '{outro_mp4.resolve()}'\n"
        )
        r = subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_txt),
            "-c:v", "libx264", "-preset", "fast", "-crf", "22",
            "-pix_fmt", "yuv420p", "-r", str(VIDEO_FPS),
            "-s", SIZE_STR, str(concat_mp4),
        ], capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            raise RuntimeError(f"Concat error:\n{r.stderr[-400:]}")

        # 5. Add music
        log.info("Adding music...")
        music     = _pick_music()
        total_dur = HOOK_DURATION_SECONDS + ANSWER_DURATION_SECONDS + OUTRO_DURATION_SECONDS
        fade_st   = total_dur - 2

        r = subprocess.run([
            "ffmpeg", "-y",
            "-i", str(concat_mp4),
            "-stream_loop", "-1", "-i", str(music),
            "-map", "0:v", "-map", "1:a",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-af", f"volume=0.28,afade=t=out:st={fade_st}:d=2",
            "-t", str(total_dur),
            str(final_mp4),
        ], capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise RuntimeError(f"Music error:\n{r.stderr[-400:]}")

        size_mb = final_mp4.stat().st_size / 1_000_000
        log.info(f"Video ready: {final_mp4.name} ({size_mb:.1f}MB, 15s, {SIZE_STR})")
        return final_mp4

    finally:
        for f in [bg_full, bg_hook, bg_answer, hook_mp4, answer_mp4,
                  outro_mp4, concat_mp4, concat_txt, comb_h, comb_a,
                  hook_ov, ans_ov, outro_png]:
            try:
                Path(f).unlink(missing_ok=True)
            except Exception:
                pass
        if pexels_raw:
            try:
                pexels_raw.unlink(missing_ok=True)
            except Exception:
                pass
