# video_creator.py
# ============================================================
# Phrase-by-phrase viral Shorts — resolution fix March 2026
#
# ROOT CAUSE OF 720x1280 BUG:
#   The -s SIZE_STR flag conflicts with -vf scale= when both
#   are present in the same FFmpeg command. FFmpeg processes
#   -vf first then -s can override unpredictably depending
#   on version. FIX: removed ALL -s flags. Resolution is now
#   controlled ONLY by scale= inside -vf filters.
# ============================================================

import json
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
    CHANNEL_NAME, FONTS_DIR, MUSIC_DIR,
    OUTRO_DURATION_SECONDS, SECONDS_PER_PHRASE,
    TEMP_DIR, VIDEO_FPS, VIDEO_HEIGHT, VIDEO_WIDTH,
    VISUAL_THEMES,
)

log = logging.getLogger("VideoCreator")

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")
MAX_PEXELS_MB  = 80

# Single source of truth for scale filter — used everywhere
SCALE_VF = f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=disable,setsar=1"

MOOD_QUERIES = {
    "attitude": [
        "wolf walking dark forest",
        "lion walking powerful close up",
        "eagle flying dramatic sky",
        "tiger stalking dark jungle",
        "silhouette man walking night city",
        "wolf pack running night",
        "lion roaring dramatic",
        "dark hawk flying storm",
    ],
    "dark_truth": [
        "dark city street night rain",
        "lone man walking rain dark",
        "crow birds dark stormy sky",
        "silhouette bridge night fog",
        "dark abandoned street dramatic",
        "man sitting alone dark room",
        "dark storm clouds lightning",
        "empty road dark night",
    ],
    "mindset": [
        "eagle soaring high sky",
        "mountain peak dramatic clouds",
        "dark ocean powerful waves",
        "tiger eyes close up intense",
        "lion staring dramatic",
        "hawk soaring sunset",
        "wolf eyes close up dark",
        "dark forest light beam",
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


# ── FFmpeg helpers ────────────────────────────────────────────

def _check_ffmpeg():
    if not shutil.which("ffmpeg"):
        raise EnvironmentError("FFmpeg not found!")


def _run_ffmpeg(cmd: list, timeout: int = 180, label: str = "") -> None:
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"FFmpeg {label} error:\n{r.stderr[-400:]}")


def _verify_resolution(path: Path) -> tuple[int, int]:
    r = subprocess.run([
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", str(path),
    ], capture_output=True, text=True, timeout=30)
    try:
        info = json.loads(r.stdout)
        for s in info.get("streams", []):
            if s.get("codec_type") == "video":
                return s["width"], s["height"]
    except Exception:
        pass
    return 0, 0


# ── Pexels ────────────────────────────────────────────────────

def _fetch_pexels_video(mood: str) -> Path | None:
    if not PEXELS_API_KEY:
        log.warning("PEXELS_API_KEY not set — gradient fallback")
        return None

    query = random.choice(MOOD_QUERIES.get(mood, MOOD_QUERIES["attitude"]))
    try:
        log.info(f"Pexels: '{query}'...")
        resp = requests.get(
            "https://api.pexels.com/videos/search",
            headers={"Authorization": PEXELS_API_KEY},
            params={
                "query":        query,
                "orientation":  "landscape",
                "size":         "large",
                "per_page":     20,
                "min_duration": 18,
            },
            timeout=20,
        )
        resp.raise_for_status()
        videos = resp.json().get("videos", [])

        if not videos:
            resp2 = requests.get(
                "https://api.pexels.com/videos/search",
                headers={"Authorization": PEXELS_API_KEY},
                params={
                    "query":        "dark dramatic animal",
                    "orientation":  "landscape",
                    "per_page":     15,
                    "min_duration": 15,
                },
                timeout=20,
            )
            resp2.raise_for_status()
            videos = resp2.json().get("videos", [])

        if not videos:
            log.warning("No Pexels results — gradient fallback")
            return None

        video = random.choice(videos[:10])
        files = video.get("video_files", [])

        hd = [f for f in files if f.get("quality") == "hd"
              and f.get("width", 9999) <= 1920]
        if not hd:
            hd = [f for f in files if f.get("quality") == "hd"] or files
        hd.sort(key=lambda f: f.get("width", 0), reverse=True)

        url = hd[0].get("link", "") if hd else ""
        if not url:
            return None

        dest       = TEMP_DIR / f"pexels_{video['id']}_{int(time.time())}.mp4"
        downloaded = 0
        dl         = requests.get(url, timeout=90, stream=True)
        dl.raise_for_status()
        with open(dest, "wb") as fh:
            for chunk in dl.iter_content(1024 * 512):
                fh.write(chunk)
                downloaded += len(chunk)
                if downloaded > MAX_PEXELS_MB * 1024 * 1024:
                    log.info(f"Size cap {MAX_PEXELS_MB}MB — stopping download")
                    break

        log.info(f"Downloaded: {dest.stat().st_size//1024//1024:.0f}MB")
        return dest

    except Exception as exc:
        log.warning(f"Pexels failed: {exc} — gradient fallback")
        return None


def _process_bg(src: Path, duration: float, out: Path) -> Path:
    """
    Landscape → centre crop 9:16 → scale to EXACT 1080×1920 → darken.
    NO -s flag — scale= in -vf is the only resolution control.
    """
    _check_ffmpeg()
    vf = (
        "crop=ih*9/16:ih:(iw-ih*9/16)/2:0,"
        f"{SCALE_VF},"
        "colorchannelmixer=rr=0.60:gg=0.60:bb=0.60"
    )
    _run_ffmpeg([
        "ffmpeg", "-y", "-i", str(src),
        "-vf", vf,
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-pix_fmt", "yuv420p", "-r", str(VIDEO_FPS),
        "-an", str(out),
    ], label="process_bg")
    return out


def _make_gradient_image(theme: dict) -> Image.Image:
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


# ── Phrase overlay ────────────────────────────────────────────

def _wrap_words(words: list, font, max_px: int,
                draw: ImageDraw.Draw) -> list[list[str]]:
    lines, cur = [], []
    for word in words:
        test = " ".join(cur + [word])
        if draw.textbbox((0, 0), test, font=font)[2] <= max_px:
            cur.append(word)
        else:
            if cur:
                lines.append(cur)
            cur = [word]
    if cur:
        lines.append(cur)
    return lines


def _render_phrase_overlay(phrase: dict, theme: dict) -> Path:
    text      = phrase.get("text", "").strip().upper()
    highlight = phrase.get("highlight", "").strip().upper()
    hi_color  = theme.get("highlight", (255, 220, 0))
    accent    = theme.get("accent_color", (255, 220, 0))

    if not text:
        text = "..."

    img  = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx   = VIDEO_WIDTH // 2

    font     = _font(108, bold=True)
    sub_font = _font(30, bold=False)
    pad_x    = 65
    max_px   = VIDEO_WIDTH - pad_x * 2
    words    = text.split()
    full_w   = draw.textbbox((0, 0), text, font=font)[2]

    def draw_word_with_shadow(x: int, y: int, word: str):
        for dx, dy in [(-3, 3), (3, 3), (-3, -3), (3, -3),
                       (0, 4), (0, -3), (-4, 0), (4, 0)]:
            draw.text((x + dx, y + dy), word, font=font,
                      fill=(0, 0, 0, 210))
        color = (*hi_color, 255) if highlight and highlight in word.upper() \
            else (255, 255, 255, 255)
        draw.text((x, y), word, font=font, fill=color)

    base_y = int(VIDEO_HEIGHT * 0.62)

    if full_w <= max_px:
        x = cx - full_w // 2
        for word in words:
            w_w = draw.textbbox((0, 0), word + " ", font=font)[2]
            draw_word_with_shadow(x, base_y, word)
            x += w_w
        text_bottom = base_y + 108 + 12
    else:
        lines   = _wrap_words(words, font, max_px, draw)
        line_h  = int(108 * 1.30)
        block_h = len(lines) * line_h
        start_y = base_y - block_h // 2
        for li, line_words in enumerate(lines):
            y         = start_y + li * line_h
            line_text = " ".join(line_words)
            line_w    = draw.textbbox((0, 0), line_text, font=font)[2]
            x         = cx - line_w // 2
            for word in line_words:
                w_w = draw.textbbox((0, 0), word + " ", font=font)[2]
                draw_word_with_shadow(x, y, word)
                x += w_w
        text_bottom = start_y + block_h + 10

    draw.text(
        (cx, text_bottom + 6),
        f"yt | {CHANNEL_NAME}",
        font=sub_font, anchor="mt",
        fill=(*accent, 170),
    )
    draw.rectangle(
        [0, VIDEO_HEIGHT - 5, VIDEO_WIDTH, VIDEO_HEIGHT],
        fill=(*accent, 210),
    )

    p = TEMP_DIR / f"ov_{int(time.time()*1000)}_{random.randint(100,999)}.png"
    img.save(str(p), "PNG")
    return p


# ── Clip builders ─────────────────────────────────────────────

def _image_to_clip(img: Path, dur: float, out: Path) -> Path:
    """PNG → video clip. Scale via -vf ONLY — no -s flag."""
    _check_ffmpeg()
    _run_ffmpeg([
        "ffmpeg", "-y", "-loop", "1", "-i", str(img),
        "-vf", SCALE_VF,
        "-t", str(dur),
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-pix_fmt", "yuv420p", "-r", str(VIDEO_FPS),
        str(out),
    ], label="image_to_clip")
    return out


def _overlay_on_clip(clip: Path, overlay: Path, out: Path) -> Path:
    """
    Composite RGBA overlay on video clip.
    Resolution forced via scale= in filter_complex ONLY — no -s flag.
    """
    _check_ffmpeg()
    _run_ffmpeg([
        "ffmpeg", "-y",
        "-i", str(clip), "-i", str(overlay),
        "-filter_complex", (
            f"[0:v]{SCALE_VF}[bg];"
            f"[1:v]{SCALE_VF}[fg];"
            "[bg][fg]overlay=0:0[v]"
        ),
        "-map", "[v]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-pix_fmt", "yuv420p", "-r", str(VIDEO_FPS),
        str(out),
    ], label="overlay_on_clip")
    return out


def _trim_clip(src: Path, start: float, dur: float, out: Path) -> Path:
    """Trim clip. Scale via -vf ONLY — no -s flag."""
    _check_ffmpeg()
    _run_ffmpeg([
        "ffmpeg", "-y",
        "-ss", str(start), "-i", str(src),
        "-t", str(dur),
        "-vf", SCALE_VF,
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-pix_fmt", "yuv420p", "-r", str(VIDEO_FPS),
        "-an", str(out),
    ], label="trim_clip")
    return out


def _outro_frame() -> Path:
    img  = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    for y in range(VIDEO_HEIGHT):
        t = y / VIDEO_HEIGHT
        draw.line([(0, y), (VIDEO_WIDTH, y)],
                  fill=(int(22*(1-t)), int(16*(1-t)), 0))

    cx, cy = VIDEO_WIDTH // 2, VIDEO_HEIGHT // 2
    gold   = (255, 210, 0)

    draw.text((cx, cy - 155), "Follow for more",
              font=_font(78, bold=True), anchor="mm",
              fill=(255, 255, 255))
    draw.ellipse([cx-68, cy-48, cx+68, cy+82],
                 fill=gold, outline=(180, 140, 0), width=4)
    draw.text((cx, cy+17), "$",
              font=_font(72, bold=True), anchor="mm",
              fill=(0, 0, 0))
    draw.text((cx, cy+125), CHANNEL_NAME,
              font=_font(56, bold=True), anchor="mm",
              fill=gold)
    draw.text((cx, cy+210), "New video every night",
              font=_font(40, bold=False), anchor="mm",
              fill=(160, 160, 160))

    p = TEMP_DIR / "frame_outro.png"
    img.save(str(p), "PNG")
    return p


def _pick_music() -> Path:
    exts   = {".mp3", ".wav", ".m4a", ".aac", ".ogg"}
    tracks = [p for p in MUSIC_DIR.iterdir() if p.suffix.lower() in exts]
    if not tracks:
        raise FileNotFoundError(f"No music in {MUSIC_DIR}/")
    return min(tracks, key=lambda p: p.stat().st_atime)


# ── Main entry point ──────────────────────────────────────────

def create_video(content_data: dict) -> Path:
    """
    Phrase-by-phrase Short at guaranteed 1080×1920.
    Resolution controlled ONLY via scale= in -vf. No -s flags anywhere.
    """
    _check_ffmpeg()
    ts      = int(time.time())
    mood    = content_data.get("mood", "attitude")
    phrases = content_data.get("phrases", [])

    if not phrases:
        hook   = content_data.get("hook", "STAY SILENT")
        answer = content_data.get("answer", "AND BUILD IN SILENCE")
        phrases = [
            {"text": hook,   "highlight": hook.split()[-1]},
            {"text": answer, "highlight": answer.split()[-1]},
        ]

    theme = VISUAL_THEMES.get(mood, VISUAL_THEMES["attitude"])
    n     = len(phrases)
    log.info(f"Creating {n}-phrase video | mood={mood} | audience={content_data.get('audience','us')}")

    phrase_dur = float(SECONDS_PER_PHRASE)
    total_main = phrase_dur * n
    total_dur  = total_main + float(OUTRO_DURATION_SECONDS)

    pexels_raw   = None
    bg_full      = TEMP_DIR / f"bg_full_{ts}.mp4"
    phrase_clips = []
    overlay_pngs = []
    outro_mp4    = TEMP_DIR / f"clip_outro_{ts}.mp4"
    concat_mp4   = TEMP_DIR / f"concat_{ts}.mp4"
    concat_txt   = TEMP_DIR / f"concat_{ts}.txt"
    raw_mp4      = TEMP_DIR / f"raw_{ts}.mp4"
    final_mp4    = TEMP_DIR / f"video_{ts}.mp4"

    try:
        # 1. Render phrase overlays
        log.info("Rendering phrase overlays...")
        for phrase in phrases:
            ov = _render_phrase_overlay(phrase, theme)
            overlay_pngs.append(ov)

        # 2. Fetch Pexels background
        log.info("Fetching Pexels background...")
        pexels_raw = _fetch_pexels_video(mood)

        # 3+4. Build phrase clips
        if pexels_raw and pexels_raw.exists():
            _process_bg(pexels_raw, total_main + 3.0, bg_full)
            for i, (phrase, ov) in enumerate(zip(phrases, overlay_pngs)):
                seg = TEMP_DIR / f"seg_{i}_{ts}.mp4"
                out = TEMP_DIR / f"clip_{i}_{ts}.mp4"
                _trim_clip(bg_full, i * phrase_dur, phrase_dur, seg)
                _overlay_on_clip(seg, ov, out)
                phrase_clips.append(out)
                seg.unlink(missing_ok=True)
        else:
            log.info("Gradient fallback...")
            for i, (phrase, ov) in enumerate(zip(phrases, overlay_pngs)):
                out    = TEMP_DIR / f"clip_{i}_{ts}.mp4"
                grad   = _make_gradient_image(theme)
                ov_img = Image.open(str(ov)).convert("RGBA")
                combined = Image.alpha_composite(
                    grad.convert("RGBA"), ov_img
                ).convert("RGB")
                comb_p = TEMP_DIR / f"comb_{i}_{ts}.png"
                combined.save(str(comb_p), "PNG")
                _image_to_clip(comb_p, phrase_dur, out)
                comb_p.unlink(missing_ok=True)
                phrase_clips.append(out)

        # 5. Outro + concat
        outro_png = _outro_frame()
        _image_to_clip(outro_png, float(OUTRO_DURATION_SECONDS), outro_mp4)
        outro_png.unlink(missing_ok=True)

        log.info(f"Concatenating {n} phrase clips + outro...")
        lines = [f"file '{c.resolve()}'\n" for c in phrase_clips]
        lines.append(f"file '{outro_mp4.resolve()}'\n")
        concat_txt.write_text("".join(lines))

        # Re-encode during concat with scale filter — no -s flag
        _run_ffmpeg([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_txt),
            "-vf", SCALE_VF,
            "-c:v", "libx264", "-preset", "fast", "-crf", "22",
            "-pix_fmt", "yuv420p", "-r", str(VIDEO_FPS),
            str(concat_mp4),
        ], timeout=180, label="concat")

        # 6. Add music
        log.info("Adding music...")
        music   = _pick_music()
        fade_st = total_dur - 2

        _run_ffmpeg([
            "ffmpeg", "-y",
            "-i", str(concat_mp4),
            "-stream_loop", "-1", "-i", str(music),
            "-map", "0:v", "-map", "1:a",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-af", f"volume=0.30,afade=t=out:st={fade_st}:d=2",
            "-t", str(total_dur),
            str(raw_mp4),
        ], timeout=60, label="music")

        # 7. Final re-encode — scale via -vf ONLY, no -s flag
        log.info("Final re-encode to guarantee 1080x1920...")
        _run_ffmpeg([
            "ffmpeg", "-y", "-i", str(raw_mp4),
            "-vf", SCALE_VF,
            "-c:v", "libx264", "-preset", "fast", "-crf", "22",
            "-pix_fmt", "yuv420p", "-r", str(VIDEO_FPS),
            "-c:a", "copy",
            str(final_mp4),
        ], timeout=120, label="final_encode")

        # 8. Verify
        w, h    = _verify_resolution(final_mp4)
        size_mb = final_mp4.stat().st_size / 1_000_000
        log.info(f"Video ready: {final_mp4.name} | {w}x{h} | {size_mb:.1f}MB | {total_dur:.0f}s")

        if w != VIDEO_WIDTH or h != VIDEO_HEIGHT:
            log.error(f"RESOLUTION MISMATCH: got {w}x{h}, expected {VIDEO_WIDTH}x{VIDEO_HEIGHT}")
        else:
            log.info(f"Resolution check: PASSED ({VIDEO_WIDTH}x{VIDEO_HEIGHT})")

        return final_mp4

    finally:
        cleanup = [bg_full, outro_mp4, concat_mp4, concat_txt, raw_mp4]
        cleanup += phrase_clips
        cleanup += overlay_pngs
        for i in range(n):
            cleanup.append(TEMP_DIR / f"seg_{i}_{ts}.mp4")
        for f in cleanup:
            try:
                Path(f).unlink(missing_ok=True)
            except Exception:
                pass
        if pexels_raw:
            try:
                pexels_raw.unlink(missing_ok=True)
            except Exception:
                pass
