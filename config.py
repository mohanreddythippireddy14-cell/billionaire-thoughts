# config.py
# ============================================================
# BillionAire's _Thoughts — Central Configuration
# Last updated: March 2026
# ============================================================

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ============================================================
# YOUR DETAILS
# ============================================================
CHANNEL_NAME      = "BillionAire's _Thoughts"
CHANNEL_EMOJI     = "😎"
ALERT_EMAIL       = "mohanreddythippireddy14@gmail.com"

# ============================================================
# API KEYS
# ============================================================
GROQ_API_KEY       = os.environ.get("GROQ_API_KEY", "")
EMAIL_SENDER       = os.environ.get("EMAIL_SENDER", ALERT_EMAIL)
EMAIL_APP_PASSWORD = os.environ.get("EMAIL_APP_PASSWORD", "")

# ============================================================
# CONTENT THEMES
# Research shows: warrior mindset, discipline, silent strength,
# hard truths, and sigma/masculine content dominate this niche.
# Each theme is a SPECIFIC angle — not generic motivation.
# ============================================================
CONTENT_THEMES = [
    "a brutal truth about why most men stay weak and never reach their potential",
    "a silent strength principle that separates high-value men from average men",
    "a hard truth about discipline that nobody wants to hear but everyone needs",
    "a dark truth about how society programs men to stay average and obedient",
    "a raw principle about self-respect and never letting people disrespect your standards",
    "a cold truth about success that soft people cannot accept",
    "a mindset shift about silence — why powerful men speak less and do more",
    "a brutal observation about why most people never change no matter what happens to them",
    "a hard truth about pain and pressure — how it either breaks or builds a man",
    "a street-smart principle about trust, loyalty and who really deserves your energy",
    "a raw truth about ambition and why most people quit right before the breakthrough",
    "a cold observation about the difference between men who win and men who complain",
    "a brutal fact about comfort zones and why staying comfortable is the slowest form of death",
    "a hard truth about time — most people waste years on people and things that don't matter",
    "a warrior mindset principle about never letting your enemies see you breaking",
    "a dark truth about why most men will never be great no matter how hard they try",
    "a cold fact about respect — it is never given, only earned through consistent action",
    "a brutal truth about the men who talk the most and achieve the least",
    "a raw principle about mental toughness and how real strength is built in silence",
    "a hard truth about why mediocre people hate watching others succeed",
]

# ============================================================
# CONTENT STYLE HINTS
# Research: 6th-grade reading level = 2x more views.
# Hook → Problem → brutal truth → short CTA works best in 2026.
# ============================================================
QUOTE_THEME = (
    "raw masculine mindset, silent strength, brutal self-improvement truths — "
    "targeting men aged 16-35 globally who want to become better"
)

QUOTE_STYLE_HINTS = [
    "raw and unfiltered — no sugar-coating, no fluff",
    "one punchy hook sentence that hits personally, followed by one brutal truth",
    "written at a 6th grade reading level — simple words, maximum impact",
    "the kind of thing a real mentor says that stops you in your tracks",
    "makes the viewer feel personally called out — they HAVE to watch till the end",
    "contrarian — challenges what most people believe about success and strength",
    "fear-based opening — highlights what someone will LOSE if they stay soft",
]

# ============================================================
# VIDEO SETTINGS
# ============================================================
VIDEO_WIDTH              = 1080
VIDEO_HEIGHT             = 1920
VIDEO_FPS                = 30
INTRO_DURATION_SECONDS   = 2
MAIN_DURATION_SECONDS    = 22
OUTRO_DURATION_SECONDS   = 3

# ============================================================
# VISUAL THEMES
# ============================================================
VISUAL_THEMES = {
    "dark_truth": {
        "bg_top":       (20, 2, 2),
        "bg_bottom":    (5, 0, 0),
        "text_color":   (255, 255, 255),
        "accent_color": (220, 40, 40),
        "glow_color":   (160, 0, 0),
        "label":        "DARK TRUTH",
    },
    "wealth_fact": {
        "bg_top":       (5, 12, 28),
        "bg_bottom":    (2, 4, 10),
        "text_color":   (255, 215, 0),
        "accent_color": (255, 215, 0),
        "glow_color":   (90, 70, 0),
        "label":        "WEALTH FACT",
    },
    "mindset": {
        "bg_top":       (18, 2, 30),
        "bg_bottom":    (6, 0, 12),
        "text_color":   (255, 255, 255),
        "accent_color": (170, 90, 255),
        "glow_color":   (70, 0, 120),
        "label":        "MINDSET",
    },
}

# ============================================================
# YOUTUBE SETTINGS
# ============================================================
YOUTUBE_PRIVACY      = "public"
YOUTUBE_CATEGORY_ID  = "26"     # 26 = Howto & Style (better for mindset/self-improvement)
YOUTUBE_LANGUAGE     = "en"
DAILY_UPLOAD_LIMIT   = 3

# ============================================================
# YOUTUBE TAGS
# Research findings (2026):
# - Use 3-5 hashtags in description — sweet spot, not spammy
# - #Shorts and #FYP are the two highest-performing universal tags
# - Mix: 1 broad + 2-3 niche + 1 viral tag
# - Hidden metadata tags (tag box) help search ranking — use long-tail
# - Attitude/sigma/discipline niche tags outperform generic motivation
# ============================================================

# These go in the description (hashtags — visible, clickable)
YOUTUBE_HASHTAGS = [
    "#Shorts",
    "#motivation",
    "#mindset",
    "#discipline",
    "#selfimprovement",
]

# These go in the hidden tag box (metadata — for search ranking)
YOUTUBE_TAGS = [
    # Broad discovery tags
    "motivation", "mindset", "self improvement", "shorts", "viral shorts",

    # High-performing niche tags for this audience
    "attitude", "discipline", "sigma male", "alpha mindset",
    "masculine energy", "silent strength", "mental toughness",
    "hustle motivation", "never give up", "hard truth",

    # Long-tail search tags (2026 research: longer queries perform better)
    "men motivation mindset", "how to be mentally strong",
    "warrior mindset motivation", "self improvement for men",
    "stop being weak motivation", "brutal truth about life",
    "discipline motivation shorts", "mindset motivation 2026",
    "attitude status shorts",
]

# ============================================================
# YOUTUBE DESCRIPTION TEMPLATE
# Research: description should have the content first (SEO),
# then a value hook, then CTA, then hashtags at the very end.
# Keep under 200 words total.
# ============================================================
YOUTUBE_DESCRIPTION_TEMPLATE = """{content}

Most people scroll past this. The ones who needed it most — stopped.

Follow for a new hard truth every day.
New video every evening at 6 PM, 7 PM & 8 PM.

{hashtags}

— {channel} {emoji}
"""

# ============================================================
# FILE PATHS — Do not change these
# ============================================================
BASE_DIR              = Path(__file__).parent
MUSIC_DIR             = BASE_DIR / "music"
FONTS_DIR             = BASE_DIR / "fonts"
TEMP_DIR              = BASE_DIR / ".temp"
LOGS_DIR              = BASE_DIR / ".logs"
YOUTUBE_TOKEN_FILE    = BASE_DIR / "youtube_token.json"
YOUTUBE_CLIENT_SECRET = BASE_DIR / "client_secret.json"

for _d in [MUSIC_DIR, FONTS_DIR, TEMP_DIR, LOGS_DIR]:
    _d.mkdir(parents=True, exist_ok=True)
