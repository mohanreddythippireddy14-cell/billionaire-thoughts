# video_creator.py
# ============================================================
# Creates viral attitude Shorts — phrase-by-phrase cut style
#
# Based on real viral channel pattern analysis:
#
#   Structure: 3-5 phrases, each phrase = one cut (2.5s)
#   + Outro (3s) = 9-15 seconds total
#
# Key visual patterns from viral channels:
#   - ONE phrase per cut, 2.5 seconds each
#   - Key word highlighted in YELLOW (or CYAN for mindset)
#   - Text in lower-centre third of screen
#   - NO watermark strip — just small channel name below text
#   - NO dark pill/box behind text — clean shadow only
#   - Bold condensed font, ALL CAPS
#   - Background changes with each cut (different Pexels clip)
#     OR same clip continues with new text overlay
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
    CHANNEL_NAME, FONTS_DIR, MUSIC_DIR,
    OUTRO_DURATION_SECONDS, SECONDS_PER_PHRASE,
    TEMP_DIR, VIDEO_FPS, VIDEO_HEIGHT, VIDEO_WIDTH,
    VISUAL_THEMES,
)

log = logging.getLogger("VideoCreator")

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")
MAX_PEXELS_MB  = 80
SIZE_STR       = f"{VIDEO_WIDTH}x{VIDEO_HEIGHT}"

# Mood → Pexels search queries
# Animal queries added based on viral channel analysis
MOOD_QUERIES = {
    "attitude": [
        "wolf walking dark", "lion walking powerful",
        "eagle flying dramatic", "tiger stalking dark",
        "silhouette man walking city", "dark confident man",
        "wolf pack night", "lion roaring close up",
    ],
    "dark_truth": [
        "dark city street night", "lone man walking rain",
        "crow birds dark sky", "dark alley dramatic",
        "silhouette bridge night", "abandoned city dark",
        "dark storm clouds dramatic", "man sitting alone dark",
    ],
    "mindset": [
        "eagle soaring sky", "mountain peak clouds",
        "dark ocean waves powerful", "tiger eyes close up",
        "lion close up dramatic", "hawk flying sunset",
        "dark forest powerful", "wolf eyes close up",
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

def _fetch_pexels_video(mood: str, query_override: str = None) -> Path | None:
    """Fetch HD landscape video. Cap at 80MB."""
    if not PEXELS_API_KEY:
        return None

    queries = MOOD_QUERIES.get(mood, MOOD_QUERIES["attitude"])
    query   = query_override or random.choice(queries)

    try:
        log.info(f"Pexels: '{query}'...")
        resp = requests.get(
            "https://api.pexels.com/videos/search",
            headers={"Authorization": PEXELS_API_KEY},
            params={"query": query, "orientation": "landscape",
                    "size": "large", "per_page": 20, "min_duration": 18},
            timeout=20,
        )
        resp.raise_for_status()
        videos = resp.json().get("videos", [])

        if not videos:
            resp2 = requests.get(
                "https://api.pexels.com/videos/search",
                headers={"Authorization": PEXELS_API_KEY},
                params={"query": "dark dramatic animal", "orientation": "landscape",
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
            hd = [f for f in files if f.get("quality") == "hd"] or files
        hd.sort(key=lambda f: f.get("width", 0), reverse=True)

        url = hd[0].get("link", "") if hd else ""
        if not url:
            return None

        dest = TEMP_DIR / f"pexels_{video['id']}_{int(time.time())}.mp4"
        dl   = requests.get(url, timeout=90, stream=True)
        dl.raise_for_status()
        downloaded = 0
        with open(dest, "wb") as fh:
            for chunk in dl.iter_content(1024 * 512):
                fh.write(chunk)
                downloaded += len(chunk)
                if downloaded > MAX_PEXELS_MB * 1024 * 1024:
                    break

        log.info(f"Downloaded: {dest.stat().st_size // 1024 // 1024:.0f}MB")
        return dest

    except Exception as exc:
        log.warning(f"Pexels failed: {exc}")
        return None


def _process_bg(src: Path, duration: float, out: Path,
                start_offset: float = 0.0) -> Path:
    """Landscape → centre crop 9:16 → 1080×1920 → darken 45% → trim."""
    _check_ffmpeg()
    vf = (
        "crop=ih*9/16:ih:(iw-ih*9/16)/2:0,"
        f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=disable,"
        "setsar=1,"
        "colorchannelmixer=rr=0.45:gg=0.45:bb=0.45"
    )
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start_offset),
        "-i", str(src),
        "-vf", vf, "-s", SIZE_STR,
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-pix_fmt", "yuv420p", "-r", str(VIDEO_FPS), "-an", str(out),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(f"BG error:\n{r.stderr[-400:]}")
    return out


def _make_gradient(theme: dict, duration: float, out: Path) -> Path:
    """Fallback gradient clip."""
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


# ── Phrase overlay renderer ───────────────────────────────────

def _render_phrase_overlay(phrase: dict, theme: dict) -> Path:
    """
    Render one phrase as transparent RGBA overlay at 1080×1920.

    Visual rules from viral channel analysis:
    - Text in LOWER-CENTRE third (55-70% from top)
    - Key word in yellow/cyan, rest in white
    - NO dark pill/box behind text — clean shadow only
    - Small channel name directly below text (not a strip)
    - Bold font, large size
    - Text shadow for readability on any background
    """
    text      = phrase["text"].upper()
    highlight = phrase["highlight"].upper()
    hi_color  = theme["highlight"]    # yellow or cyan
    accent    = theme["accent_color"]

    img  = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx   = VIDEO_WIDTH // 2

    font     = _font(96, bold=True)
    sub_font = _font(28, bold=False)

    # ── Render text with highlighted word ─────────────────────
    # Split text into words, find the highlight word
    words       = text.split()
    hi_word_idx = -1
    for i, w in enumerate(words):
        if highlight in w:
            hi_word_idx = i
            break

    # Measure full line width first
    full_text_w = draw.textbbox((0, 0), text, font=font)[2]

    # If text fits on one line, render inline with colour split
    if full_text_w <= VIDEO_WIDTH - 80:
        # Position: 58% from top (lower-centre third)
        y = int(VIDEO_HEIGHT * 0.58)

        # Draw shadow for each word
        x = cx - full_text_w // 2
        for word in words:
            w_width = draw.textbbox((0, 0), word + " ", font=font)[2]
            for dx, dy in [(-2, 2), (2, 2), (-2, -2), (2, -2), (0, 3)]:
                draw.text((x + dx, y + dy), word, font=font,
                          fill=(0, 0, 0, 200))
            # Draw word in correct colour
            color = (*hi_color, 255) if highlight in word else (255, 255, 255, 255)
            draw.text((x, y), word, font=font, fill=color)
            x += w_width

    else:
        # Word wrap — each wrapped line rendered
        pad_x  = 70
        max_px = VIDEO_WIDTH - pad_x * 2
        lines  = _wrap_words(words, font, max_px, draw)
        line_h = int(96 * 1.3)
        block_h = len(lines) * line_h
        start_y = int(VIDEO_HEIGHT * 0.55) - block_h // 2

        for li, line_words in enumerate(lines):
            y         = start_y + li * line_h
            line_text = " ".join(line_words)
            line_w    = draw.textbbox((0, 0), line_text, font=font)[2]
            x         = cx - line_w // 2

            for word in line_words:
                w_width = draw.textbbox((0, 0), word + " ", font=font)[2]
                for dx, dy in [(-2, 2), (2, 2), (-2, -2), (2, -2), (0, 3)]:
                    draw.text((x + dx, y + dy), word, font=font,
                              fill=(0, 0, 0, 200))
                color = (*hi_color, 255) if highlight in word else (255, 255, 255, 255)
                draw.text((x, y), word, font=font, fill=color)
                x += w_width

    # ── Small channel name below text ─────────────────────────
    # Get approximate text bottom position
    text_bottom = int(VIDEO_HEIGHT * 0.58) + 96 + 10
    draw.text(
        (cx, text_bottom + 8),
        f"yt | {CHANNEL_NAME}",
        font=sub_font, anchor="mt",
        fill=(*accent, 180),
    )

    # Thin accent line at very bottom
    draw.rectangle([0, VIDEO_HEIGHT - 4, VIDEO_WIDTH, VIDEO_HEIGHT],
                   fill=(*accent, 200))

    p = TEMP_DIR / f"phrase_{phrase['text'][:10].replace(' ','_')}_{int(time.time()*1000)}.png"
    img.save(str(p), "PNG")
    return p


def _wrap_words(words: list, font, max_px: int,
                draw: ImageDraw.Draw) -> list[list[str]]:
    """Wrap a list of words into lines fitting max_px."""
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


# ── Outro frame ───────────────────────────────────────────────

def _outro_frame() -> Path:
    """Gold gradient outro — follow CTA."""
    img  = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    for y in range(VIDEO_HEIGHT):
        t = y / VIDEO_HEIGHT
        draw.line([(0, y), (VIDEO_WIDTH, y)],
                  fill=(int(22*(1-t)), int(16*(1-t)), 0))

    cx, cy = VIDEO_WIDTH // 2, VIDEO_HEIGHT // 2
    gold   = (255, 210, 0)

    draw.text((cx, cy - 155), "Follow for more",
              font=_font(78, bold=True), anchor="mm", fill=(255, 255, 255))

    # Gold coin
    draw.ellipse([cx-68, cy-48, cx+68, cy+82],
                 fill=gold, outline=(180, 140, 0), width=4)
    draw.text((cx, cy+17), "$",
              font=_font(72, bold=True), anchor="mm", fill=(0, 0, 0))

    draw.text((cx, cy + 125), CHANNEL_NAME,
              font=_font(56, bold=True), anchor="mm", fill=gold)
    draw.text((cx, cy + 210), "New video every night",
              font=_font(40, bold=False), anchor="mm", fill=(160, 160, 160))

    p = TEMP_DIR / "frame_outro.png"
    img.save(str(p), "PNG")
    return p


# ── FFmpeg helpers ────────────────────────────────────────────

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
        "-pix_fmt", "yuv420p", "-r", str(VIDEO_FPS), str(out),
    ], capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(f"Clip error:\n{r.stderr[-400:]}")
    return out


def _overlay_on_clip(clip: Path, overlay: Path, out: Path) -> Path:
    """Composite RGBA overlay on video clip."""
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
        "-pix_fmt", "yuv420p", "-r", str(VIDEO_FPS), str(out),
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


# ── Main entry point ──────────────────────────────────────────

def create_video(content_data: dict) -> Path:
    """
    Assemble phrase-by-phrase Short:
      Phrase 1 (2.5s) + Phrase 2 (2.5s) + ... + Outro (3s)
      Each phrase on its own segment of the Pexels background.
      Total: 9-15 seconds.
    """
    _check_ffmpeg()
    ts      = int(time.time())
    mood    = content_data.get("mood", "attitude")
    phrases = content_data.get("phrases", [])

    if not phrases:
        # Fallback: build phrases from hook/answer
        hook   = content_data.get("hook", "")
        answer = content_data.get("answer", "")
        phrases = [
            {"text": hook,   "highlight": hook.split()[-1]   if hook   else ""},
            {"text": answer, "highlight": answer.split()[-1] if answer else ""},
        ]

    theme = VISUAL_THEMES.get(mood, VISUAL_THEMES["attitude"])
    n     = len(phrases)
    log.info(f"Creating video | mood={mood} | {n} phrases | audience={content_data.get('audience','us')}")

    phrase_dur  = float(SECONDS_PER_PHRASE)
    total_main  = phrase_dur * n
    total_dur   = total_main + OUTRO_DURATION_SECONDS

    # Temp paths
    pexels_raw  = None
    bg_full     = TEMP_DIR / f"bg_full_{ts}.mp4"
    phrase_clips = []
    outro_mp4   = TEMP_DIR / f"clip_outro_{ts}.mp4"
    concat_mp4  = TEMP_DIR / f"concat_{ts}.mp4"
    concat_txt  = TEMP_DIR / f"concat_{ts}.txt"
    final_mp4   = TEMP_DIR / f"video_{ts}.mp4"
    overlay_pngs = []

    try:
        # 1. Render all phrase overlays
        log.info("Rendering phrase overlays...")
        for i, phrase in enumerate(phrases):
            ov = _render_phrase_overlay(phrase, theme)
            overlay_pngs.append(ov)

        # 2. Fetch ONE Pexels background for the whole video
        log.info("Fetching Pexels background...")
        pexels_raw = _fetch_pexels_video(mood)

        if pexels_raw and pexels_raw.exists():
            # Process full background
            _process_bg(pexels_raw, total_main + 2.0, bg_full)

            # Create one clip per phrase — each is a segment of the same background
            # This creates a smooth continuous background with text changing
            for i, (phrase, ov) in enumerate(zip(phrases, overlay_pngs)):
                start  = i * phrase_dur
                bg_seg = TEMP_DIR / f"bg_seg_{i}_{ts}.mp4"
                out_cl = TEMP_DIR / f"clip_phrase_{i}_{ts}.mp4"

                _trim_clip(bg_full, start, phrase_dur, bg_seg)
                _overlay_on_clip(bg_seg, ov, out_cl)
                phrase_clips.append(out_cl)

        else:
            # Gradient fallback
            log.info("Gradient fallback...")
            for i, (phrase, ov) in enumerate(zip(phrases, overlay_pngs)):
                grad    = TEMP_DIR / f"grad_{i}_{ts}.png"
                bg_clip = TEMP_DIR / f"bg_seg_{i}_{ts}.mp4"
                out_cl  = TEMP_DIR / f"clip_phrase_{i}_{ts}.mp4"

                # Draw gradient
                img  = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT))
                draw = ImageDraw.Draw(img)
                top, bot = theme["bg_top"], theme["bg_bottom"]
                for y in range(VIDEO_HEIGHT):
                    t = y / VIDEO_HEIGHT
                    draw.line([(0, y), (VIDEO_WIDTH, y)], fill=(
                        int(top[0]+(bot[0]-top[0])*t),
                        int(top[1]+(bot[1]-top[1])*t),
                        int(top[2]+(bot[2]-top[2])*t),
                    ))
                img.save(str(grad), "PNG")

                _image_to_clip(grad, phrase_dur, bg_clip)
                overlay = Image.open(str(ov)).convert("RGBA")
                base    = Image.open(str(grad)).convert("RGBA")
                combined_path = TEMP_DIR / f"combined_{i}_{ts}.png"
                Image.alpha_composite(base, overlay).convert("RGB").save(str(combined_path))
                _image_to_clip(combined_path, phrase_dur, out_cl)
                phrase_clips.append(out_cl)

                for f in [grad, bg_clip, combined_path]:
                    Path(f).unlink(missing_ok=True)

        # 3. Outro clip
        outro_png = _outro_frame()
        _image_to_clip(outro_png, float(OUTRO_DURATION_SECONDS), outro_mp4)

        # 4. Concatenate all phrase clips + outro
        log.info(f"Concatenating {len(phrase_clips)} phrase clips + outro...")
        lines = [f"file '{c.resolve()}'\n" for c in phrase_clips]
        lines.append(f"file '{outro_mp4.resolve()}'\n")
        concat_txt.write_text("".join(lines))

        r = subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_txt),
            "-c:v", "libx264", "-preset", "fast", "-crf", "22",
            "-pix_fmt", "yuv420p", "-r", str(VIDEO_FPS),
            "-s", SIZE_STR, str(concat_mp4),
        ], capture_output=True, text=True, timeout=180)
        if r.returncode != 0:
            raise RuntimeError(f"Concat error:\n{r.stderr[-400:]}")

        # 5. Add music
        log.info("Adding music...")
        music    = _pick_music()
        fade_st  = total_dur - 2

        r = subprocess.run([
            "ffmpeg", "-y",
            "-i", str(concat_mp4),
            "-stream_loop", "-1", "-i", str(music),
            "-map", "0:v", "-map", "1:a",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-af", f"volume=0.30,afade=t=out:st={fade_st}:d=2",
            "-t", str(total_dur),
            str(final_mp4),
        ], capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise RuntimeError(f"Music error:\n{r.stderr[-400:]}")

        size_mb = final_mp4.stat().st_size / 1_000_000
        log.info(f"Video ready: {final_mp4.name} ({size_mb:.1f}MB, {total_dur:.0f}s, {SIZE_STR})")
        return final_mp4

    finally:
        # Clean up all temp files
        cleanup = [bg_full, outro_mp4, concat_mp4, concat_txt]
        cleanup += phrase_clips
        cleanup += overlay_pngs
        # Also clean bg segments
        for i in range(n):
            cleanup.append(TEMP_DIR / f"bg_seg_{i}_{ts}.mp4")
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
