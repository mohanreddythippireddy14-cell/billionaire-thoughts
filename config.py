# config.py
# ============================================================
# BillionAire's _Thoughts — Central Configuration
# Updated: March 2026 — phrase-by-phrase cut structure
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
CHANNEL_NAME  = os.environ.get("CHANNEL_NAME", "")
CHANNEL_EMOJI = "😎"
ALERT_EMAIL   = os.environ.get("ALERT_EMAIL", "")

# ============================================================
# API KEYS
# ============================================================
GROQ_API_KEY       = os.environ.get("GROQ_API_KEY", "")
EMAIL_SENDER       = os.environ.get("EMAIL_SENDER", "")
EMAIL_APP_PASSWORD = os.environ.get("EMAIL_APP_PASSWORD", "")

# ============================================================
# AUDIENCE TARGETING
# ============================================================
TARGET_AUDIENCE = os.environ.get("TARGET_AUDIENCE", "us")

# ============================================================
# VIDEO STRUCTURE — phrase-by-phrase cuts
#
# Each quote is broken into 3-5 short phrases.
# Each phrase gets its own cut (2-3 seconds on screen).
# Total: 15 seconds max.
#
# Example:
#   Phrase 1: "A MAN BECOMES"          (2.5s)
#   Phrase 2: "HE LEARNED HOW TO"      (2.5s)
#   Phrase 3: "CONTROL HIS EMOTIONS"   (2.5s)
#   Phrase 4: "AND IGNORE GIRLS"       (2.5s)
#   Outro:    Follow CTA               (3s)
#   Total: 13s
#
# Each phrase: 2-3 seconds on screen
# Outro: 3 seconds
# Max total: 15 seconds
# ============================================================
SECONDS_PER_PHRASE     = 2.5   # each phrase stays on screen this long
OUTRO_DURATION_SECONDS = 3
MAX_PHRASES            = 5     # max 5 phrases per quote

VIDEO_WIDTH  = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS    = 30

# ============================================================
# AUDIENCE PROFILES
# ============================================================
AUDIENCE_PROFILES = {

    "us": {
        "name":      "US Audience",
        "age_group": "16-35 English-speaking males globally",
        "style": (
            "Raw, direct, attitude-driven. Short punchy phrases. "
            "Speaks to universal human experiences — being judged, "
            "staying silent while building, proving people wrong. "
            "Feels like something you'd write on a wall."
        ),
        "themes": [
            "a man who controls his emotions controls his life",
            "karma always finds the people who hurt others without reason",
            "every downfall is the beginning of the greatest comeback",
            "14 years of school never taught you how to be free",
            "never run after people who would never run for you",
            "the wolf doesn't explain itself to sheep",
            "be confident like an eagle — it never worries about the opinion of chickens",
            "silence is the best answer to someone who doesn't deserve your words",
            "the people who doubted you are watching every move you make now",
            "stop looking for loyalty in people who are only loyal to convenience",
            "your struggle today is building the version of you that wins tomorrow",
            "a lion doesn't lose sleep over the opinion of sheep",
            "work in silence and let your results make the noise",
            "everything changes when you stop caring what people think of you",
            "just because it is taking more time doesn't mean it is not happening",
            "never explain yourself to people who are committed to misunderstanding you",
            "the strongest men are not the loudest ones in the room",
            "if you hurt someone without reason be ready because karma never forgets",
            "real respect is earned in silence not announced with words",
            "the man who masters himself masters everything around him",
        ],
        "tags": [
            "motivation", "mindset", "attitude", "shorts", "viral shorts",
            "self improvement", "discipline", "hard truth", "mental strength",
            "attitude shorts", "motivational quotes", "sigma mindset",
            "never give up", "warrior mindset", "beast mode attitude",
        ],
        "hashtags":        ["#Shorts", "#motivation", "#attitude", "#mindset", "#hardtruth"],
        "description_cta": "Follow for daily attitude. New video every night.",
    },

    "europe": {
        "name":      "European Audience",
        "age_group": "18-34 European males",
        "style": (
            "Stoic, philosophical, calm but devastating. "
            "Short phrases that expose what society programs people to believe. "
            "Each phrase builds on the last."
        ),
        "themes": [
            "society programs you to be average but you were not born average",
            "a stoic man never wastes words on people who cannot understand silence",
            "every scar you carry is proof that you survived what was meant to break you",
            "the system was designed for obedience not greatness — choose greatness",
            "the wisest men throughout history all shared one thing — they spoke last",
            "pain is the price of becoming someone most people never dare to be",
            "a man who controls his emotions is more dangerous than any weapon",
            "society fears the man who thinks for himself because he cannot be controlled",
            "real strength is not shown in the gym it is shown in silence under pressure",
            "the man who needs no validation from anyone has already won the hardest battle",
            "stop explaining yourself to people who already decided what to think of you",
            "discipline is choosing what you want most over what you want right now",
            "the uncomfortable truth is that most people choose comfort over greatness",
            "your reputation is built in silence your character is built in adversity",
            "be like water — calm on the surface unstoppable underneath",
        ],
        "tags": [
            "stoicism", "mindset", "philosophy", "shorts", "self improvement",
            "stoic motivation", "discipline", "mental strength",
            "stoic wisdom", "dark truth", "philosophical truth",
        ],
        "hashtags":        ["#Shorts", "#stoicism", "#mindset", "#philosophy", "#discipline"],
        "description_cta": "Follow for daily stoic truths. New video every night.",
    },

    "asia": {
        "name":      "Asian Audience",
        "age_group": "16-30 Asian males — India, Pakistan, SEA, Middle East",
        "style": (
            "Poetic, struggle-based, validates sacrifice. "
            "Speaks to someone building from nothing. "
            "Short phrases with emotional weight."
        ),
        "themes": [
            "the man who came from nothing has a fire that cannot be extinguished",
            "stay silent while you build because loud men get copied before they win",
            "your background does not define your destination — your discipline does",
            "the ones who doubted you will one day ask how you did it",
            "prove people wrong not with words but with the life you build",
            "a tiger does not need to announce its presence — its arrival is enough",
            "real men are built in struggle not comfort — embrace the difficulty",
            "working when everyone else is sleeping is how the silent ones win",
            "respect is never given to men who come from nothing — it is taken",
            "karma will return everything to everyone — just focus on your path",
            "the heaviest weights build the strongest men — do not run from pressure",
            "your story is not finished yet — the best chapter is still being written",
            "wait in silence build in patience strike with results",
            "the man who survives the most becomes the one everyone looks up to",
            "never let them see you breaking — break alone then rise in front of everyone",
        ],
        "tags": [
            "motivation", "attitude", "mindset", "shorts", "viral shorts",
            "attitude status", "self improvement", "discipline",
            "men motivation", "attitude quotes", "never give up",
            "attitude motivation", "powerful motivation", "sigma mindset",
        ],
        "hashtags":        ["#Shorts", "#motivation", "#attitude", "#mindset", "#discipline"],
        "description_cta": "Follow for daily hard truths. New video every night.",
    },
}

# ── Active profile ────────────────────────────────────────────
_ACTIVE            = AUDIENCE_PROFILES.get(TARGET_AUDIENCE, AUDIENCE_PROFILES["us"])
CONTENT_THEMES     = _ACTIVE["themes"]
YOUTUBE_TAGS       = _ACTIVE["tags"]
YOUTUBE_HASHTAGS   = _ACTIVE["hashtags"]
DESCRIPTION_CTA    = _ACTIVE["description_cta"]
AUDIENCE_STYLE     = _ACTIVE["style"]
AUDIENCE_AGE_GROUP = _ACTIVE["age_group"]

# ============================================================
# VISUAL THEMES — mood determines Pexels search + accent colour
# ============================================================
VISUAL_THEMES = {
    "dark_truth": {
        "bg_top":       (20, 2, 2),
        "bg_bottom":    (5, 0, 0),
        "accent_color": (220, 40, 40),
        "highlight":    (255, 220, 0),   # yellow word highlight
        "label":        "DARK TRUTH",
    },
    "attitude": {
        "bg_top":       (8, 8, 8),
        "bg_bottom":    (0, 0, 0),
        "accent_color": (255, 220, 0),
        "highlight":    (255, 220, 0),   # yellow
        "label":        "ATTITUDE",
    },
    "mindset": {
        "bg_top":       (18, 2, 30),
        "bg_bottom":    (6, 0, 12),
        "accent_color": (170, 90, 255),
        "highlight":    (0, 220, 255),   # cyan like in the reference videos
        "label":        "MINDSET",
    },
}

# ============================================================
# YOUTUBE SETTINGS
# ============================================================
YOUTUBE_PRIVACY     = "public"
YOUTUBE_CATEGORY_ID = "26"
YOUTUBE_LANGUAGE    = "en"
DAILY_UPLOAD_LIMIT  = 3

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
