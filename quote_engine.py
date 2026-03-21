# quote_engine.py
# ============================================================
# Generates phrase-by-phrase attitude/motivational content.
#
# Fixes:
#   - No fake stats (97%, 83% etc) — explicitly banned
#   - Post-generation validation strips any percentage numbers
#   - 6 viral quote structures in rotation
#   - Audience-aware prompts per TARGET_AUDIENCE
#   - Natural phrase boundaries enforced with good/bad examples
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

QUOTE_STRUCTURES = [
    {
        "name": "BUILD_UP",
        "desc": "4 phrases that build tension — each adds one more layer to a truth about a man",
        "example": '"A MAN BECOMES" / "HE LEARNED HOW TO" / "CONTROL HIS EMOTIONS" / "AND IGNORE DISTRACTIONS"',
        "mood": "attitude",
    },
    {
        "name": "IF_THEN",
        "desc": "IF condition → action → consequence → karma. 4 phrases.",
        "example": '"IF YOU HURT SOMEONE" / "WITHOUT ANY REASON" / "THEN BE READY" / "KARMA NEVER FORGETS"',
        "mood": "dark_truth",
    },
    {
        "name": "REFRAME",
        "desc": "Takes a painful word and reframes it as hidden strength. 3 phrases.",
        "example": '"Every DOWNFALL IS" / "The OPPORTUNITY" / "Greatest COMEBACK"',
        "mood": "mindset",
    },
    {
        "name": "DARK_TRUTH",
        "desc": "Escalating dark observations about how life really works. 3 short punchy phrases.",
        "example": '"YEARS IN SCHOOL" / "FOR A SMALL JOB" / "THAT IS NOT LIFE"',
        "mood": "dark_truth",
    },
    {
        "name": "ANIMAL_POWER",
        "desc": "Animal analogy for attitude and silent strength. 2-3 phrases.",
        "example": '"BE CONFIDENT LIKE EAGLE" / "SILENT LIKE A WOLF" / "DEADLY LIKE A TIGER"',
        "mood": "attitude",
    },
    {
        "name": "NEVER_DO",
        "desc": "Things a real man never does. 4 short phrases each a complete thought.",
        "example": '"NEVER CHASE PEOPLE" / "WHO WALK AWAY" / "LET THEM GO" / "AND RISE ALONE"',
        "mood": "attitude",
    },
]

BANNED_WORDS = [
    "never give up", "keep going", "believe in yourself",
    "work hard", "hustle", "grind", "stay positive",
    "dream big", "you got this", "seize the day",
    "rise and shine", "be the best",
]

STAT_PATTERN = re.compile(r'\b\d+\s*%|\b\d+\s*percent', re.IGNORECASE)


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


def _contains_stat(text: str) -> bool:
    return bool(STAT_PATTERN.search(text))


def _contains_banned(text: str) -> bool:
    t = text.lower()
    return any(b in t for b in BANNED_WORDS)


def _load_analytics_ideas() -> list:
    f = LOGS_DIR / "next_week_ideas.json"
    if not f.exists():
        return []
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
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


def generate_content() -> dict:
    """
    Generate phrase-by-phrase quote with natural splits.
    """
    theme     = _pick_theme()
    audience  = TARGET_AUDIENCE
    structure = random.choice(QUOTE_STRUCTURES)

    log.info(f"Audience: {audience} | Structure: {structure['name']} | Theme: {theme[:55]}...")

    prompt = f"""You create viral attitude and motivational YouTube Shorts content.

CHANNEL: "{CHANNEL_NAME}"
AUDIENCE: {AUDIENCE_AGE_GROUP}
TONE: {AUDIENCE_STYLE}
TOPIC: {theme}
STRUCTURE TO USE: {structure['name']}
STRUCTURE DESCRIPTION: {structure['desc']}
EXAMPLE OF THIS STRUCTURE: {structure['example']}

WRITE A NEW QUOTE using the {structure['name']} structure about: {theme}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
THE MOST IMPORTANT RULE — NATURAL PHRASE SPLITTING:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Each phrase MUST be a complete grammatical unit that makes
sense when read alone AND connects naturally to the next phrase.

Think of it like a spoken pause — split where a person
would naturally pause when reading aloud.

GOOD splits — each phrase is a complete thought or clause:
  "THE STRONGEST MEN" / "NEVER ANNOUNCE" / "THEIR NEXT MOVE"
  "IF YOU STAY SILENT" / "WHILE THEY TALK" / "YOU ALREADY WON"
  "REAL POWER" / "IS NOT GIVEN" / "IT IS BUILT IN DARKNESS"
  "A LION DOES NOT" / "EXPLAIN ITSELF" / "TO SHEEP"

BAD splits — phrases cut mid-thought and make no sense alone:
  "THE STRONGEST" / "MEN NEVER" / "ANNOUNCE THEIR" / "NEXT MOVE"
  "IF YOU STAY" / "SILENT WHILE" / "THEY TALK YOU" / "ALREADY WON"
  "REAL" / "POWER IS" / "NOT GIVEN IT" / "IS BUILT"

The test: read each phrase alone. Does it make sense?
If not — you split in the wrong place.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OTHER STRICT RULES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. 3 to 5 phrases total. Each phrase = 3 to 6 words MAX.
2. ALL CAPS for power words, Mixed Case for softer connectors.
3. highlight = the ONE word in that phrase with most emotional weight.
4. Last phrase = hardest hitting — the "wahh" moment.
5. NO percentages or statistics. Use "most", "few", "many" instead.
6. FORBIDDEN: never give up, hustle, grind, work hard, believe in yourself.
7. FORBIDDEN topics: relationships — self-improvement only.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Return ONLY valid JSON — zero text before or after:
{{
  "phrases": [
    {{"text": "PHRASE ONE", "highlight": "ONEWORD"}},
    {{"text": "PHRASE TWO", "highlight": "ONEWORD"}},
    {{"text": "PHRASE THREE", "highlight": "ONEWORD"}},
    {{"text": "PHRASE FOUR", "highlight": "ONEWORD"}}
  ],
  "mood": "EXACTLY ONE of: attitude | dark_truth | mindset",
  "title": "50-60 chars, hook in first 4 words, 1 emoji, impossible not to click",
  "description": "Two sentences about the quote. No hashtags. No percentages."
}}"""

    data = None
    for attempt in range(3):
        raw  = _call_groq(prompt, temperature=0.90 + attempt * 0.03)
        data = _parse_json(raw)

        has_stat   = any(_contains_stat(p.get("text", ""))   for p in data.get("phrases", []))
        has_banned = any(_contains_banned(p.get("text", "")) for p in data.get("phrases", []))

        if not has_stat and not has_banned:
            break

        if has_stat:
            log.warning(f"Attempt {attempt+1}: fake stat — retrying")
        if has_banned:
            log.warning(f"Attempt {attempt+1}: banned phrase — retrying")

        if attempt == 2:
            for p in data.get("phrases", []):
                p["text"] = STAT_PATTERN.sub("many", p.get("text", ""))
            log.warning("Stripped stats on final attempt")

    if not data or "phrases" not in data or len(data.get("phrases", [])) < 2:
        raise ValueError("Not enough phrases generated")
    for field in ["mood", "title"]:
        if field not in data or not str(data[field]).strip():
            raise ValueError(f"Missing field: '{field}'")

    if data["mood"] not in ["attitude", "dark_truth", "mindset"]:
        data["mood"] = structure.get("mood", "attitude")

    data["phrases"] = data["phrases"][:MAX_PHRASES]

    cleaned = []
    for p in data["phrases"]:
        text      = str(p.get("text", "")).strip()
        highlight = str(p.get("highlight", "")).strip()
        if not text:
            continue
        text  = STAT_PATTERN.sub("many", text)
        words = text.split()
        if len(words) > 7:
            text = " ".join(words[:6])
        if not highlight or highlight.upper() not in text.upper():
            highlight = text.split()[-1]
        cleaned.append({"text": text, "highlight": highlight.upper()})

    if len(cleaned) < 2:
        raise ValueError("Not enough valid phrases after cleaning")

    data["phrases"]     = cleaned
    data["description"] = data.get("description", "") or " ".join(p["text"] for p in cleaned)
    data["content"]     = " ".join(p["text"] for p in cleaned)
    data["hook"]        = cleaned[0]["text"]
    data["answer"]      = cleaned[-1]["text"]
    data["audience"]    = audience
    data["structure"]   = structure["name"]

    log.info(f"Generated | mood={data['mood']} | {len(cleaned)} phrases | {structure['name']}")
    for i, p in enumerate(cleaned):
        log.info(f"  [{i+1}] {p['text']}  (yellow: {p['highlight']})")

    return data
