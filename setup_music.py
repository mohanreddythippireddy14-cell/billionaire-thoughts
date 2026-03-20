# setup_music.py
# ============================================================
# Downloads 5 free royalty-free trap/energetic beats.
# Run ONCE on your Windows PC, then commit music/ to GitHub.
#
# All tracks are from Pixabay (royalty-free, safe for YouTube monetization)
# Run:  python setup_music.py
# ============================================================

import sys
from pathlib import Path

import requests

MUSIC_DIR = Path("music")
MUSIC_DIR.mkdir(exist_ok=True)

# Free royalty-free tracks from Pixabay CDN
# These are dark/energetic/trap beats — perfect for finance content
TRACKS = [
    {
        "name":  "trap_01.mp3",
        "title": "Dark Trap Beat",
        "url":   "https://cdn.pixabay.com/download/audio/2023/06/13/audio_9e5eb15534.mp3",
    },
    {
        "name":  "trap_02.mp3",
        "title": "Aggressive Hip Hop",
        "url":   "https://cdn.pixabay.com/download/audio/2022/10/25/audio_946b2ba8cb.mp3",
    },
    {
        "name":  "trap_03.mp3",
        "title": "Dark Cinematic",
        "url":   "https://cdn.pixabay.com/download/audio/2022/11/22/audio_febc508520.mp3",
    },
    {
        "name":  "trap_04.mp3",
        "title": "Motivation Trap",
        "url":   "https://cdn.pixabay.com/download/audio/2023/01/17/audio_6ff46e3671.mp3",
    },
    {
        "name":  "trap_05.mp3",
        "title": "Power Beat",
        "url":   "https://cdn.pixabay.com/download/audio/2023/03/09/audio_1af4b6c414.mp3",
    },
]

print("=" * 55)
print("  Downloading Free Music — BillionAire's_Thoughts 😎")
print("=" * 55)
print(f"\nDownloading {len(TRACKS)} royalty-free tracks...\n")

ok = 0
for t in TRACKS:
    dest = MUSIC_DIR / t["name"]
    if dest.exists() and dest.stat().st_size > 10_000:
        print(f"  ✓ Already downloaded: {t['title']}")
        ok += 1
        continue
    try:
        print(f"  Downloading: {t['title']}...", end=" ", flush=True)
        r = requests.get(t["url"], timeout=60, stream=True)
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        kb = dest.stat().st_size // 1024
        print(f"✓ ({kb} KB)")
        ok += 1
    except Exception as exc:
        print(f"✗ Failed ({exc})")
        print(f"    → Manually download a free MP3 and save it as music/{t['name']}")
        print(f"    → Free source: https://pixabay.com/music (search 'trap')")

print(f"\n{ok}/{len(TRACKS)} tracks ready.\n")

if ok == 0:
    print("❌  No tracks downloaded.")
    print("   Add any MP3 file to the music/ folder manually, then re-run.")
    sys.exit(1)

print("✅  Next steps:")
print("    git add music/")
print('    git commit -m "Add music tracks"')
print("    git push")
print("\nAfter pushing, GitHub Actions can access these tracks on every run.")
