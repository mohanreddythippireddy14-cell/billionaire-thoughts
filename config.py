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
# AUDIENCE TARGETING
# Each upload targets a different timezone audience.
# GitHub Actions passes TARGET_AUDIENCE as env variable.
#
# Upload schedule (UTC):
#   Asia   — 15:30 UTC = 9:00 PM IST
#   Europe — 22:00 UTC = 3:30 AM IST
#   US     — 20:00 UTC = 1:30 AM IST
# ============================================================
TARGET_AUDIENCE = os.environ.get("TARGET_AUDIENCE", "us")

# ============================================================
# VIDEO STRUCTURE — 27 seconds, NO intro
#
#   0:00 - 0:08   Hook          (8s)  — bold text slams in instantly
#   0:08 - 0:18   Answer       (10s)  — brutal reveal
#   0:18 - 0:21   Comment bait  (3s)  — thought-provoking question
#   0:21 - 0:24   Agree/disagree(3s)  — CTA for comments
#   0:24 - 0:27   Outro         (3s)  — follow CTA
# ============================================================
HOOK_DURATION_SECONDS           = 8
ANSWER_DURATION_SECONDS         = 10
COMMENT_BAIT_DURATION_SECONDS   = 3
AGREE_DISAGREE_DURATION_SECONDS = 3
OUTRO_DURATION_SECONDS          = 3
MAIN_DURATION_SECONDS           = HOOK_DURATION_SECONDS + ANSWER_DURATION_SECONDS  # 18s

VIDEO_WIDTH   = 1080
VIDEO_HEIGHT  = 1920
VIDEO_FPS     = 30

# ============================================================
# AUDIENCE PROFILES
# Same niche, different cultural angle per audience
# ============================================================
AUDIENCE_PROFILES = {

    "us": {
        "name":       "US Audience",
        "age_group":  "16-30 American males",
        "style": (
            "Aggressive, direct, money-focused, no-excuses tone. "
            "Use specific stats and numbers. Fear of missing out. "
            "Self-made mindset. Examples: '97% of men...', "
            "'by age 30', '$1M difference'."
        ),
        "hook_style": "Fear-based — what they will LOSE if they stay soft",
        "themes": [
            "a cold truth about why 97% of American men will retire broke and regret it",
            "a brutal fact about why most men in their 20s are wasting their best years",
            "a hard truth about discipline that separates the top 3% from everyone else",
            "a dark observation about why men who complain never build real wealth",
            "a raw truth about silence — why the most successful men say the least",
            "a cold fact about comfort — how choosing comfort at 25 destroys your 40s",
            "a brutal truth about why most men quit right before the breakthrough",
            "a hard reality about time — the most expensive thing men waste in their 20s",
            "a dark truth about why average men hate watching others succeed",
            "a cold principle about self-respect — why weak men get walked over their whole life",
            "a brutal observation about men who talk about their goals but never execute",
            "a raw truth about ambition — why most men are afraid of their own potential",
            "a cold hard fact about money — what broke men believe that rich men don't",
            "a dark truth about loyalty — most men give it to people who would never return it",
            "a brutal reality about age — why your 20s are your only real window to change",
        ],
        "tags": [
            "motivation", "mindset", "self improvement", "shorts", "viral shorts",
            "sigma male", "discipline", "alpha mindset", "mental toughness",
            "hard truth", "men motivation", "self improvement for men",
            "stop being weak motivation", "brutal truth about life",
            "warrior mindset motivation", "discipline motivation shorts",
            "attitude shorts", "mindset motivation 2026",
        ],
        "hashtags":        ["#Shorts", "#motivation", "#mindset", "#discipline", "#selfimprovement"],
        "description_cta": "Follow for daily hard truths. New video every night.",
    },

    "europe": {
        "name":       "European Audience",
        "age_group":  "18-34 European males",
        "style": (
            "Stoic, intellectual, philosophical tone. Cold logic over emotion. "
            "Reference class systems, societal programming, historical truths. "
            "Calm but devastating. Examples: 'Society teaches you...', "
            "'The system is designed to...', 'Men who understand this...'."
        ),
        "hook_style": "Truth-based — exposing what society deliberately hides",
        "themes": [
            "a stoic truth about how modern society programs men to stay obedient and mediocre",
            "a philosophical observation about why most men never question the life they were given",
            "a cold logical truth about discipline that stoic philosophers understood centuries ago",
            "a dark truth about the class system — why most men work hard but stay poor",
            "a raw observation about why men who think for themselves are feared by society",
            "a brutal stoic principle about pain — why avoiding it destroys a man's character",
            "a cold truth about loyalty — most men give it to people who would never reciprocate",
            "a philosophical truth about ambition — why society punishes men who want more",
            "a dark observation about how comfort is the modern man's greatest enemy",
            "a stoic principle about silence — why the wisest men speak only when necessary",
            "a cold truth about the education system — what it teaches and what it deliberately hides",
            "a stoic observation about anger — why men who control it are more dangerous than those who don't",
            "a philosophical truth about failure — why every stoic treated it as necessary not optional",
            "a dark observation about social media — how it was designed to keep men distracted and weak",
            "a brutal stoic principle about expectations — why most men suffer because of what they expect",
        ],
        "tags": [
            "stoicism", "mindset", "self improvement", "shorts", "philosophy",
            "stoic", "marcus aurelius", "discipline", "mental toughness",
            "stoic motivation", "stoic wisdom", "men motivation",
            "how to think clearly", "stoicism for men", "dark truth about life",
            "philosophical truth", "stoic shorts", "mindset 2026",
        ],
        "hashtags":        ["#Shorts", "#stoicism", "#mindset", "#philosophy", "#selfimprovement"],
        "description_cta": "Follow for daily stoic truths. New video every night.",
    },

    "asia": {
        "name":       "Asian Audience",
        "age_group":  "16-30 Asian males — India, Pakistan, SEA, Middle East",
        "style": (
            "Philosophical, struggle-based, family honour, rising from nothing tone. "
            "Poetic but punchy. Reference hard work, proving people wrong, "
            "silent sacrifice, building from zero. Emotional but disciplined. "
            "Examples: 'The man who came from nothing...', "
            "'Stay silent, let results speak', 'Your struggle is building you'."
        ),
        "hook_style": "Wisdom-based — truth that validates their struggle and sacrifice",
        "themes": [
            "a raw truth about why men who come from nothing have an unfair advantage over the privileged",
            "a powerful principle about silent sacrifice — working in darkness until results speak",
            "a hard truth about proving people wrong — why actions matter more than words ever will",
            "a brutal observation about why men who face the most struggle build the strongest character",
            "a deep truth about loyalty — who truly stands with you when everything in life fails",
            "a raw principle about staying silent while you build — never announce your next move",
            "a hard truth about men who were told they would never make it and proved everyone wrong",
            "a powerful observation about patience — why men who wait and work always outlast the loud",
            "a dark truth about society judging men by their background and not their potential",
            "a raw principle about mental strength — how pressure either reveals or builds a man's true self",
            "a brutal truth about family expectations — the weight that either breaks or motivates a man",
            "a powerful observation about the men who smile in public and suffer in silence",
            "a raw truth about respect — it is never given to men who come from nothing, only taken",
            "a hard truth about sacrifice — what the most successful men gave up that others never will",
            "a philosophical truth about time — why the man who respects it most always wins in the end",
        ],
        "tags": [
            "motivation", "attitude", "mindset", "shorts", "viral shorts",
            "attitude status", "self improvement", "discipline",
            "motivational shorts", "men motivation", "attitude quotes",
            "hard work motivation", "success motivation", "never give up",
            "attitude shayari", "mindset motivation", "sigma mindset",
            "attitude motivation shorts", "powerful motivation",
        ],
        "hashtags":        ["#Shorts", "#motivation", "#attitude", "#mindset", "#discipline"],
        "description_cta": "Follow for daily hard truths. New video every night.",
    },
}

# ── Active profile (set by TARGET_AUDIENCE env var) ───────────
_ACTIVE             = AUDIENCE_PROFILES.get(TARGET_AUDIENCE, AUDIENCE_PROFILES["us"])
CONTENT_THEMES      = _ACTIVE["themes"]
YOUTUBE_TAGS        = _ACTIVE["tags"]
YOUTUBE_HASHTAGS    = _ACTIVE["hashtags"]
DESCRIPTION_CTA     = _ACTIVE["description_cta"]
AUDIENCE_STYLE      = _ACTIVE["style"]
AUDIENCE_HOOK_STYLE = _ACTIVE["hook_style"]
AUDIENCE_AGE_GROUP  = _ACTIVE["age_group"]

# ============================================================
# VISUAL THEMES
# ============================================================
VISUAL_THEMES = {
    "dark_truth": {
        "bg_top":       (20, 2, 2),
        "bg_bottom":    (5, 0, 0),
        "text_color":   (255, 255, 255),
        "accent_color": (220, 40, 40),
        "label":        "DARK TRUTH",
    },
    "wealth_fact": {
        "bg_top":       (5, 12, 28),
        "bg_bottom":    (2, 4, 10),
        "text_color":   (255, 215, 0),
        "accent_color": (255, 215, 0),
        "label":        "WEALTH FACT",
    },
    "mindset": {
        "bg_top":       (18, 2, 30),
        "bg_bottom":    (6, 0, 12),
        "text_color":   (255, 255, 255),
        "accent_color": (170, 90, 255),
        "label":        "MINDSET",
    },
}

# ============================================================
# YOUTUBE SETTINGS
# ============================================================
YOUTUBE_PRIVACY      = "public"
YOUTUBE_CATEGORY_ID  = "26"
YOUTUBE_LANGUAGE     = "en"
DAILY_UPLOAD_LIMIT   = 3

# ============================================================
# YOUTUBE DESCRIPTION TEMPLATE
# ============================================================
YOUTUBE_DESCRIPTION_TEMPLATE = """{content}

{description_cta}

{hashtags}

— {channel} {emoji}
"""

# ============================================================
# FILE PATHS
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
