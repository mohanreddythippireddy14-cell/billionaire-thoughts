# config.py
# ============================================================
# BillionAire's _Thoughts — Central Configuration
# All your settings live here. Edit this file to change anything.
# ============================================================

import os
from pathlib import Path

# Load .env file when running locally on Windows
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ============================================================
# YOUR DETAILS
# ============================================================
CHANNEL_NAME     = "BillionAire's _Thoughts"
CHANNEL_EMOJI    = "😎"
ALERT_EMAIL      = "mohanreddythippireddy14@gmail.com"

# ============================================================
# API KEYS — Never put real values here.
# Set these as GitHub Secrets (see SETUP_GUIDE.md).
# ============================================================
GROQ_API_KEY      = os.environ.get("GROQ_API_KEY", "")
EMAIL_SENDER      = os.environ.get("EMAIL_SENDER", ALERT_EMAIL)
EMAIL_APP_PASSWORD = os.environ.get("EMAIL_APP_PASSWORD", "")

# ============================================================
# CONTENT — What kind of finance content to generate
# ============================================================
# These are the themes Groq will randomly pick from each run.
# You can add, remove, or edit these at any time.
CONTENT_THEMES = [
    "a shocking money fact with a specific number or statistic most people don't know",
    "a dark truth about how money and society actually work that rich people know",
    "a wealth mindset rule that separates rich thinking from poor thinking",
    "a counterintuitive money principle that sounds wrong but is mathematically true",
    "an uncomfortable financial truth that most people refuse to accept",
    "a specific habit or behaviour that keeps 95% of people broke their whole life",
    "a little-known fact about how billionaires actually built their wealth",
    "a financial myth that schools teach that actively makes people poorer",
]

# ============================================================
# VIDEO SETTINGS
# ============================================================
VIDEO_WIDTH              = 1080    # pixels (9:16 portrait for Shorts)
VIDEO_HEIGHT             = 1920    # pixels
VIDEO_FPS                = 30
INTRO_DURATION_SECONDS   = 2       # branded intro
MAIN_DURATION_SECONDS    = 22      # main content (keep under 27s total)
OUTRO_DURATION_SECONDS   = 3       # follow CTA
# Total = 2 + 22 + 3 = 27 seconds — perfect for Shorts

# ============================================================
# VISUAL THEMES — AI picks one of these based on content mood
# Each mood gets its own color scheme
# ============================================================
VISUAL_THEMES = {
    "dark_truth": {
        # Deep crimson — used for shocking / dark content
        "bg_top":       (20, 2, 2),
        "bg_bottom":    (5, 0, 0),
        "text_color":   (255, 255, 255),
        "accent_color": (220, 40, 40),
        "glow_color":   (160, 0, 0),
        "label":        "DARK TRUTH",
    },
    "wealth_fact": {
        # Deep navy with gold — used for money facts
        "bg_top":       (5, 12, 28),
        "bg_bottom":    (2, 4, 10),
        "text_color":   (255, 215, 0),
        "accent_color": (255, 215, 0),
        "glow_color":   (90, 70, 0),
        "label":        "WEALTH FACT",
    },
    "mindset": {
        # Deep purple — used for mindset tips
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
YOUTUBE_CATEGORY_ID  = "27"     # 27 = Education (better CPM than People & Blogs)
YOUTUBE_LANGUAGE     = "en"
DAILY_UPLOAD_LIMIT   = 3        # YouTube API allows 6/day; we use 3

YOUTUBE_TAGS = [
    "finance", "money", "wealth", "rich", "millionaire",
    "investing", "financial freedom", "money mindset",
    "wealth tips", "financial tips", "shorts", "viral shorts",
    "money facts", "billionaire", "get rich", "passive income",
    "financial literacy", "money secrets", "rich mindset",
]

YOUTUBE_DESCRIPTION_TEMPLATE = """{content}

💰 Follow for daily wealth secrets that schools never taught you.
👉 New video every evening — 6 PM, 7 PM & 8 PM.

#finance #money #wealth #millionaire #financialfreedom #shorts
#moneymindset #rich #investing #billionaire #financialtips

— {channel} {emoji}
"""

# ============================================================
# FILE PATHS — Do not change these
# ============================================================
BASE_DIR               = Path(__file__).parent
MUSIC_DIR              = BASE_DIR / "music"
FONTS_DIR              = BASE_DIR / "fonts"
TEMP_DIR               = BASE_DIR / ".temp"
LOGS_DIR               = BASE_DIR / ".logs"
YOUTUBE_TOKEN_FILE     = BASE_DIR / "youtube_token.json"
YOUTUBE_CLIENT_SECRET  = BASE_DIR / "client_secret.json"

# Create directories if they don't exist
for _d in [MUSIC_DIR, FONTS_DIR, TEMP_DIR, LOGS_DIR]:
    _d.mkdir(parents=True, exist_ok=True)
