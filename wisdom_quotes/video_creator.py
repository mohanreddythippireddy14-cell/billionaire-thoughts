import os
import random
import textwrap
import subprocess
import requests
from PIL import Image, ImageDraw, ImageFont

PEXELS_API_KEY = os.environ["PEXELS_API_KEY"]
PEXELS_URL = "https://api.pexels.com/v1/search"
MUSIC_DIR = "music"
OUTPUT_PATH = "wisdom_quotes/output.mp4"
COMPOSITE_PATH = "wisdom_quotes/composite.jpg"

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


def _draw_text_on_image(img_path, quote_text, author):
    img = Image.open(img_path).convert("RGB")
    img = img.resize((1080, 1920), Image.LANCZOS)

    draw = ImageDraw.Draw(img)

    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
    quote_font = ImageFont.truetype(font_path, 48)
    author_font = ImageFont.truetype(font_path, 36)

    # Wrap quote text
    lines = textwrap.wrap(quote_text, width=22)
    line_height = 60
    total_height = len(lines) * line_height
    y = (1920 - total_height) // 2 - 60
    x = 80

    for line in lines:
        # Shadow
        draw.text((x + 2, y + 2), line, font=quote_font, fill=(0, 0, 0, 180))
        # Main text
        draw.text((x, y), line, font=quote_font, fill=(255, 255, 255))
        y += line_height

    # Author bottom right
    author_text = f"— {author}"
    bbox = draw.textbbox((0, 0), author_text, font=author_font)
    author_w = bbox[2] - bbox[0]
    ax = 1080 - author_w - 80
    ay = y + 30
    draw.text((ax + 2, ay + 2), author_text, font=author_font, fill=(0, 0, 0, 180))
    draw.text((ax, ay), author_text, font=author_font, fill=(255, 255, 255, 220))

    img.save(COMPOSITE_PATH, quality=95)
    return COMPOSITE_PATH


def create_video(quote: str) -> str:
    bg_path = _fetch_pexels_image()
    music_path = _pick_music()

    parts = quote.split(" — ", 1)
    quote_text = parts[0].strip()
    author = parts[1].strip() if len(parts) > 1 else ""

    composite = _draw_text_on_image(bg_path, quote_text, author)

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", composite,
        "-i", music_path,
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
    
