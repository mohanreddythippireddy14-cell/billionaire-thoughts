import os
import random
import textwrap
import subprocess
import requests


PEXELS_API_KEY = os.environ["PEXELS_API_KEY"]
PEXELS_URL = "https://api.pexels.com/v1/search"
MUSIC_DIR = "music"  # reuse existing music folder from root
OUTPUT_PATH = "wisdom_quotes/output.mp4"

NATURE_QUERIES = [
    "cinematic nature landscape",
    "mountain fog dramatic",
    "ocean waves cinematic",
    "forest light rays",
    "sunset dramatic sky",
    "misty mountains",
    "dark forest cinematic",
]

VIDEO_DURATION = 20  # seconds


def _fetch_pexels_image():
    query = random.choice(NATURE_QUERIES)
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": query, "orientation": "portrait", "per_page": 15}

    r = requests.get(PEXELS_URL, headers=headers, params=params)
    r.raise_for_status()
    photos = r.json().get("photos", [])

    if not photos:
        raise ValueError(f"No Pexels results for query: {query}")

    photo = random.choice(photos)
    img_url = photo["src"]["portrait"]

    img_path = "wisdom_quotes/bg.jpg"
    img_data = requests.get(img_url).content
    with open(img_path, 'wb') as f:
        f.write(img_data)

    print(f"Downloaded background: {img_url}")
    return img_path


def _pick_music():
    tracks = [f for f in os.listdir(MUSIC_DIR) if f.endswith(".mp3")]
    if not tracks:
        raise FileNotFoundError("No music tracks found in music/")
    return os.path.join(MUSIC_DIR, random.choice(tracks))


def _wrap_quote(quote, width=28):
    """Wrap quote for drawtext. Returns escaped string with \\n line breaks."""
    lines = textwrap.wrap(quote, width=width)
    # Escape single quotes for FFmpeg, join with \n
    escaped = r"\n".join(line.replace("'", r"'\''") for line in lines)
    return escaped


def create_video(quote: str) -> str:
    bg_path = _fetch_pexels_image()
    music_path = _pick_music()
    wrapped = _wrap_quote(quote)

    # Font path — use a system font available on Ubuntu runners
    font = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"

    # x offset: slightly left of center (~80px left of true center)
    # y: vertically centered
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", bg_path,
        "-i", music_path,
        "-vf",
        (
            f"scale=1080:1920,"
            f"drawtext=fontfile={font}:"
            f"text='{wrapped}':"
            f"x=(w-text_w)/2-80:"
            f"y=(h-text_h)/2:"
            f"fontsize=52:"
            f"fontcolor=white:"
            f"line_spacing=18:"
            f"borderw=3:"
            f"bordercolor=black@0.6"
        ),
        "-t", str(VIDEO_DURATION),
        "-shortest",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        OUTPUT_PATH
    ]

    subprocess.run(cmd, check=True)
    print(f"Video created: {OUTPUT_PATH}")
    return OUTPUT_PATH
