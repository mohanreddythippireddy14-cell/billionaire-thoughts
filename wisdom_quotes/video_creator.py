import os
import random
import textwrap
import subprocess
import requests

PEXELS_API_KEY = os.environ["PEXELS_API_KEY"]
PEXELS_URL = "https://api.pexels.com/v1/search"
MUSIC_DIR = "music"
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

VIDEO_DURATION = 20


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
    with open(img_path, 'wb') as f:
        f.write(requests.get(img_url).content)
    print(f"Downloaded background: {img_url}")
    return img_path


def _pick_music():
    tracks = [f for f in os.listdir(MUSIC_DIR) if f.endswith(".mp3")]
    if not tracks:
        raise FileNotFoundError("No music tracks found in music/")
    return os.path.join(MUSIC_DIR, random.choice(tracks))


def _escape(text):
    return text.replace("'", r"'\''").replace(":", r"\:")


def _wrap_quote(quote_text, width=22):
    lines = textwrap.wrap(quote_text, width=width)
    return r"\n".join(_escape(line) for line in lines)


def create_video(quote: str) -> str:
    bg_path = _fetch_pexels_image()
    music_path = _pick_music()

    # Split quote and author
    parts = quote.split(" — ", 1)
    quote_text = parts[0].strip()
    author = f"— {parts[1].strip()}" if len(parts) > 1 else ""

    wrapped = _wrap_quote(quote_text)
    author_escaped = _escape(author)

    font = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", bg_path,
        "-i", music_path,
        "-vf",
        (
            f"scale=1080:1920,"
            f"drawtext=fontfile={font}:text='{wrapped}':"
            f"x=80:y=(h-text_h)/2-60:"
            f"fontsize=38:fontcolor=white:line_spacing=20:"
            f"borderw=3:bordercolor=black@0.7,"
            f"drawtext=fontfile={font}:text='{author_escaped}':"
            f"x=w-text_w-80:y=(h+text_h)/2+40:"
            f"fontsize=30:fontcolor=white@0.85:"
            f"borderw=2:bordercolor=black@0.5"
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
