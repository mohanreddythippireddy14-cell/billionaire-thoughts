# quote_engine.py
# ============================================================
# Generates attitude/motivational content — phrase-by-phrase.
#
# Based on real viral pattern analysis:
#   - Quote split into 3-5 short phrases (3-6 words each)
#   - Each phrase shown for 2.5 seconds on its own cut
#   - One key word per phrase marked for yellow/cyan highlight
#   - 6 quote structures identified from viral channels
#
# Quote structures:
#   BUILD_UP    — builds tension phrase by phrase
#   IF_THEN     — condition → consequence → karma
#   REFRAME     — reframes a negative into a positive
#   DARK_TRUTH  — escalating dark observations about life
#   ANIMAL      — animal analogy for attitude/strength
#   NEVER_DO    — list of things a real man never does
# ============================================================

import datetime
import json
import logging
import os
import random
import re

import httpx
from groq import Groq
from tenacity import (
    before_sleep_log, retry, stop_after_attempt, wait_exponential,
)

from config import (
    GROQ_API_KEY, CONTENT_THEMES, CHANNEL_NAME,
    LOGS_DIR, TARGET_AUDIENCE,
    AUDIENCE_STYLE, AUDIENCE_AGE_GROUP,
    MAX_PHRASES,
)

log        = logging.getLogger("QuoteEngine")
GROQ_MODEL = "llama-3.1-8b-instant"
_CLIENT    = None

# Quote structure types — picked randomly each run for variety
QUOTE_STRUCTURES = [
    {
        "name": "BUILD_UP",
        "description": "Builds tension across 4 phrases. Each phrase adds one more layer.",
        "example": [
            {"text": "A MAN BECOMES", "highlight": "MAN"},
            {"text": "HE LEARNED HOW TO", "highlight": "LEARNED"},
            {"text": "CONTROL HIS EMOTIONS", "highlight": "EMOTIONS"},
            {"text": "AND IGNORE GIRLS", "highlight": "IGNORE"},
        ],
        "mood": "attitude",
    },
    {
        "name": "IF_THEN",
        "description": "IF condition → build up → THEN consequence → karma payback. 4 phrases.",
        "example": [
            {"text": "IF YOU HURT SOMEONE", "highlight": "HURT"},
            {"text": "WITHOUT ANY REASON", "highlight": "REASON"},
            {"text": "THEN BE READY", "highlight": "READY"},
            {"text": "KARMA WILL PAY BACK", "highlight": "KARMA"},
        ],
        "mood": "dark_truth",
    },
    {
        "name": "REFRAME",
        "description": "Takes a negative word and reframes it as strength. 3 phrases.",
        "example": [
            {"text": "Every DOWNFALL IS", "highlight": "DOWNFALL"},
            {"text": "The OPPORTUNITY", "highlight": "OPPORTUNITY"},
            {"text": "Greatest COMEBACK", "highlight": "COMEBACK"},
        ],
        "mood": "mindset",
    },
    {
        "name": "DARK_TRUTH",
        "description": "Escalating dark observations about modern life. 3 phrases.",
        "example": [
            {"text": "14 YEARS IN SCHOOL", "highlight": "SCHOOL"},
            {"text": "FOR A 30K JOB", "highlight": "30K"},
            {"text": "THAT'S NOT LIFE", "highlight": "LIFE"},
        ],
        "mood": "dark_truth",
    },
    {
        "name": "ANIMAL_ANALOGY",
        "description": "Animal analogy for attitude. 2-3 short punchy phrases.",
        "example": [
            {"text": "BE CONFIDENT LIKE EAGLE", "highlight": "EAGLE"},
            {"text": "BEAST LIKE A TIGER", "highlight": "TIGER"},
            {"text": "SILENT LIKE A WOLF", "highlight": "WOLF"},
        ],
        "mood": "attitude",
    },
    {
        "name": "NEVER_DO",
        "description": "Things a real man never does. 4-5 short phrases.",
        "example": [
            {"text": "NEVER RUN FOR", "highlight": "RUN"},
            {"text": "A PERSON", "highlight": "PERSON"},
            {"text": "WHO NEVER", "highlight": "NEVER"},
            {"text": "WAITED FOR YOU", "highlight": "WAITED"},
        ],
        "mood": "attitude",
    },
]

# Forbidden clichés
BANNED = [
    "never give up", "keep going", "believe in yourself", "work hard",
    "hustle", "grind", "stay positive", "dream big", "you got this",
    "seize the day", "be the best", "rise and shine",
]


def _init_groq() -> Groq:
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not set.")
    http    = httpx.Client(timeout=60.0, trust_env=False)
    _CLIENT = Groq(api_key=GROQ_API_KEY, http_client=http)
    return _CLIENT


@retry(
    reraise=True,
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    before_sleep=before_sleep_log(log, logging.WARNING),
)
def _call_groq(prompt: str, temperature: float = 0.93) -> str:
    client = _init_groq()
    resp   = client.chat.completions.create(
        model       = GROQ_MODEL,
        messages    = [{"role": "user", "content": prompt}],
        temperature = temperature,
    )
    return resp.choices[0].message.content.strip()


def _parse_json(raw: str) -> dict:
    raw = re.sub(r"```(?:json)?\s*", "", raw).strip().replace("```", "")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    start = raw.find('{')
    if start == -1:
        raise ValueError(f"No JSON:\n{raw[:200]}")
    depth = 0
    for i, ch in enumerate(raw[start:], start):
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return json.loads(raw[start:i+1])
    raise ValueError(f"Unclosed JSON:\n{raw[:200]}")


def _load_analytics_ideas() -> list:
    f = LOGS_DIR / "next_week_ideas.json"
    if not f.exists():
        return []
    try:
        data        = json.loads(f.read_text(encoding="utf-8"))
        valid_until = datetime.date.fromisoformat(data.get("valid_until", "2000-01-01"))
        if valid_until < datetime.date.today():
            return []
        return data.get("ideas", [])
    except Exception:
        return []


def _pick_theme() -> str:
    ideas = _load_analytics_ideas()
    pool  = ideas if ideas else CONTENT_THEMES
    return random.choice(pool)


def _contains_banned(text: str) -> bool:
    t = text.lower()
    return any(b in t for b in BANNED)


def generate_content() -> dict:
    """
    Generate phrase-by-phrase quote content.

    Returns dict with:
      phrases  — list of {text, highlight} dicts (3-5 items)
                 text: the phrase shown on screen (3-6 words, ALL CAPS)
                 highlight: one key word to show in yellow
      mood     — attitude | dark_truth | mindset
      structure — which quote structure was used
      title    — YouTube title
      description — 2 sentences
      content  — full quote joined (for description/backward compat)
      audience — target audience
    """
    theme     = _pick_theme()
    audience  = TARGET_AUDIENCE
    structure = random.choice(QUOTE_STRUCTURES)

    log.info(f"Audience: {audience} | Structure: {structure['name']} | Theme: {theme[:55]}...")

    # Build example string for the prompt
    example_lines = "\n".join(
        f'  {{"text": "{p["text"]}", "highlight": "{p["highlight"]}"}}'
        for p in structure["example"]
    )

    prompt = f"""You create viral attitude and motivational content for YouTube Shorts.

CHANNEL: "{CHANNEL_NAME}"
AUDIENCE: {AUDIENCE_AGE_GROUP}
TONE: {AUDIENCE_STYLE}
TOPIC: {theme}
STRUCTURE: {structure["name"]} — {structure["description"]}

EXAMPLE OF THIS STRUCTURE:
{example_lines}

YOUR TASK:
Write a brand new quote using the {structure["name"]} structure.
The quote should be about: {theme}

RULES FOR PHRASES:
- 3 to 5 phrases total
- Each phrase: 3 to 6 words maximum — SHORT and PUNCHY
- ALL CAPS for hard-hitting words, Mixed Case for softer ones
- Each phrase must stand alone but connect to the next
- The last phrase must be the most powerful — the "wahh" moment
- highlight: ONE key word per phrase that carries the most emotional weight
- FORBIDDEN: never give up, hustle, grind, work hard, believe in yourself
- NO fake statistics, NO percentages

RULES FOR TITLE:
- 50-60 characters
- Hook in first 4 words
- 1 emoji
- Makes someone stop scrolling

Return ONLY valid JSON — nothing before or after:
{{
  "phrases": [
    {{"text": "PHRASE ONE HERE", "highlight": "KEYWORD"}},
    {{"text": "PHRASE TWO HERE", "highlight": "KEYWORD"}},
    {{"text": "PHRASE THREE HERE", "highlight": "KEYWORD"}},
    {{"text": "PHRASE FOUR HERE", "highlight": "KEYWORD"}}
  ],
  "mood": "EXACTLY ONE of: attitude | dark_truth | mindset",
  "title": "YouTube title here with emoji",
  "description": "Two sentences expanding on the quote. No hashtags."
}}"""

    raw  = _call_groq(prompt, temperature=0.93)
    data = _parse_json(raw)

    # Validate
    if "phrases" not in data or not data["phrases"]:
        raise ValueError("Missing 'phrases' field")
    if len(data["phrases"]) < 2:
        raise ValueError("Need at least 2 phrases")
    for field in ["mood", "title"]:
        if field not in data or not str(data[field]).strip():
            raise ValueError(f"Missing field: '{field}'")

    # Sanitize mood
    if data["mood"] not in ["attitude", "dark_truth", "mindset"]:
        data["mood"] = structure.get("mood", "attitude")

    # Clamp to MAX_PHRASES
    data["phrases"] = data["phrases"][:MAX_PHRASES]

    # Ensure each phrase has text + highlight
    cleaned = []
    for p in data["phrases"]:
        text      = str(p.get("text", "")).strip()
        highlight = str(p.get("highlight", "")).strip()
        if not text:
            continue
        # Trim long phrases
        words = text.split()
        if len(words) > 7:
            text = " ".join(words[:6])
        # If highlight not in text, pick last word
        if highlight.upper() not in text.upper():
            highlight = text.split()[-1]
        cleaned.append({"text": text, "highlight": highlight})

    if len(cleaned) < 2:
        raise ValueError("Not enough valid phrases after cleaning")

    data["phrases"]   = cleaned
    data["description"] = data.get("description", "") or " ".join(p["text"] for p in cleaned)
    data["content"]   = " ".join(p["text"] for p in cleaned)
    data["audience"]  = audience
    data["structure"] = structure["name"]
    data["hook"]      = cleaned[0]["text"]   # backward compat
    data["answer"]    = cleaned[-1]["text"]  # backward compat

    log.info(f"Generated | mood={data['mood']} | structure={structure['name']} | {len(cleaned)} phrases")
    for i, p in enumerate(cleaned):
        log.info(f"  [{i+1}] {p['text']}  (highlight: {p['highlight']})")

    return data
