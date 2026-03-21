# config.py
# ============================================================
# BillionAire's _Thoughts — Central Configuration
# Updated: March 2026 — 15-second structure
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
# ============================================================
TARGET_AUDIENCE = os.environ.get("TARGET_AUDIENCE", "us")

# ============================================================
# VIDEO STRUCTURE — 15 seconds total
#
#   0:00 - 0:05   Hook     (5s)  — stops the scroll
#   0:05 - 0:12   Answer   (7s)  — revelation, reframes reality
#   0:12 - 0:15   Outro    (3s)  — follow CTA
#
# Why 15s:
#   - Higher completion rate = algorithm pushes harder
#   - Forces tighter, more impactful writing
#   - Viewers re-watch — counts as multiple views
# ============================================================
HOOK_DURATION_SECONDS   = 5
ANSWER_DURATION_SECONDS = 7
OUTRO_DURATION_SECONDS  = 3
MAIN_DURATION_SECONDS   = HOOK_DURATION_SECONDS + ANSWER_DURATION_SECONDS  # 12s

VIDEO_WIDTH   = 1080
VIDEO_HEIGHT  = 1920
VIDEO_FPS     = 30

# ============================================================
# AUDIENCE PROFILES
# ============================================================
AUDIENCE_PROFILES = {

    "us": {
        "name":       "US Audience",
        "age_group":  "16-35 English-speaking males globally",
        "style": (
            "Raw, direct, no fluff. Speaks to the universal human fear of "
            "wasting your life, being judged, staying average. "
            "Short sentences. Punches hard. Feels like a mentor who "
            "won't lie to you."
        ),
        "themes": [
            "the uncomfortable truth about why most people never change",
            "what separates men who build something from men who just dream",
            "the real reason people stay in situations that are killing them",
            "what silence and discipline build that loud people never understand",
            "the truth about why being judged by others means you're doing something right",
            "what most people get wrong about strength and what it actually looks like",
            "the painful truth about comfort and what it quietly costs you",
            "why the men who say the least are usually building the most",
            "what happens to your life when you stop caring what people think",
            "the truth about failure that no one tells you until it's too late",
            "what real confidence looks like versus the fake kind everyone performs",
            "why people who've been through the most are usually the hardest to break",
            "the truth about loyalty and who is really in your corner when things go wrong",
            "what most men will regret at 40 that they're choosing right now",
            "the quiet difference between men who make it and men who almost made it",
        ],
        "tags": [
            "motivation", "mindset", "attitude", "shorts", "viral shorts",
            "self improvement", "discipline", "hard truth", "mental strength",
            "men motivation", "attitude shorts", "mindset motivation",
            "brutal truth", "silent strength", "warrior mindset",
            "motivational quotes", "life advice", "success mindset",
        ],
        "hashtags":        ["#Shorts", "#motivation", "#mindset", "#attitude", "#hardtruth"],
        "description_cta": "Follow for daily hard truths. New video every night.",
    },

    "europe": {
        "name":       "European Audience",
        "age_group":  "18-34 European males",
        "style": (
            "Stoic, philosophical, cold logic. Exposes what society "
            "programs people to believe. Calm but devastating. "
            "Speaks to the person who thinks deeply but acts slowly."
        ),
        "themes": [
            "what stoicism teaches about pain that modern society refuses to accept",
            "the uncomfortable truth about how society programs people to stay average",
            "what the men who built empires understood about silence and patience",
            "the philosophical truth about why most people suffer unnecessarily",
            "what happens when a man stops asking for permission to become great",
            "the cold truth about why comfort is the most dangerous thing in modern life",
            "what history's most resilient men had in common that no one talks about",
            "the truth about why men who think for themselves are always misunderstood",
            "what stoic philosophy says about the opinion of others and why it means nothing",
            "the brutal reality about time that most men refuse to face until it's gone",
            "what separates men who endure from men who collapse under pressure",
            "the philosophical truth about identity and why most people never find theirs",
            "what the wisest men throughout history understood about staying silent",
            "why the men who've suffered the most are the ones you should never underestimate",
            "the cold truth about loyalty that most people learn too late in life",
        ],
        "tags": [
            "stoicism", "mindset", "philosophy", "shorts", "self improvement",
            "stoic", "marcus aurelius", "discipline", "mental toughness",
            "stoic motivation", "stoic wisdom", "philosophical truth",
            "dark truth about life", "stoic shorts", "mindset 2026",
        ],
        "hashtags":        ["#Shorts", "#stoicism", "#mindset", "#philosophy", "#discipline"],
        "description_cta": "Follow for daily stoic truths. New video every night.",
    },

    "asia": {
        "name":       "Asian Audience",
        "age_group":  "16-30 Asian males — India, Pakistan, SEA, Middle East",
        "style": (
            "Poetic but direct. Validates struggle and sacrifice. "
            "Speaks to someone building from zero, proving people wrong, "
            "working in silence. Emotional but disciplined. Relatable."
        ),
        "themes": [
            "what the men who came from nothing understand about hunger that privileged men never will",
            "the truth about why working in silence is more powerful than announcing your goals",
            "what sacrifice really means and why the people who sacrifice the most say the least",
            "the hard truth about being underestimated and why it is actually your advantage",
            "what happens to a man who keeps going when everyone around him has given up",
            "the truth about proving people wrong — why your results are the only reply that matters",
            "what silent men are building while loud men are still talking about their plans",
            "the painful truth about who is really watching you fail and who is really in your corner",
            "what pressure does to a man who refuses to break — and why it makes him dangerous",
            "the truth about respect — it is never given to men who come from nothing, only earned",
            "what the most resilient men in history had that most people today have lost",
            "the truth about family expectations and the weight that either breaks or builds you",
            "why the men who struggled the most are the ones the world eventually kneels to",
            "what happens when a quiet man runs out of patience — and why you should not be there",
            "the truth about timing — why the men who wait and work always outlast the ones who rush",
        ],
        "tags": [
            "motivation", "attitude", "mindset", "shorts", "viral shorts",
            "attitude status", "self improvement", "discipline",
            "motivational shorts", "men motivation", "attitude quotes",
            "hard work motivation", "never give up", "attitude motivation",
            "powerful motivation", "mindset motivation", "sigma mindset",
        ],
        "hashtags":        ["#Shorts", "#motivation", "#attitude", "#mindset", "#discipline"],
        "description_cta": "Follow for daily hard truths. New video every night.",
    },
}

# ── Active profile ────────────────────────────────────────────
_ACTIVE             = AUDIENCE_PROFILES.get(TARGET_AUDIENCE, AUDIENCE_PROFILES["us"])
CONTENT_THEMES      = _ACTIVE["themes"]
YOUTUBE_TAGS        = _ACTIVE["tags"]
YOUTUBE_HASHTAGS    = _ACTIVE["hashtags"]
DESCRIPTION_CTA     = _ACTIVE["description_cta"]
AUDIENCE_STYLE      = _ACTIVE["style"]
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
