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
#   - JSON parse errors retry instead of crashing pipeline
#   - Comprehensive character sanitization — handles all punctuation,
#     smart quotes, dashes, brackets, unicode etc. permanently
# ============================================================

import datetime
import json
import logging
import os
import random
import re
import unicodedata

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
        "desc": "4 escalating lines. Each line deepens transformation. Final line delivers identity shift.",
        "example": '"A MAN CHANGES" / "WHEN HE STOPS EXPLAINING" / "STARTS OBSERVING EVERYTHING" / "AND TRUSTS NO ONE EASILY"',
        "mood": "attitude",
    },
    {
        "name": "IF_THEN",
        "desc": "Condition → hidden truth → warning → inevitable outcome.",
        "example": '"IF YOU PLAY WITH LOYALTY" / "LIKE IT IS NOTHING" / "REMEMBER THIS" / "SILENCE RETURNS DIFFERENT"',
        "mood": "dark_truth",
    },
    {
        "name": "REFRAME",
        "desc": "Turn weakness into controlled strength. 3 tight lines.",
        "example": '"REJECTION IS NOT LOSS" / "IT IS FILTERING PEOPLE" / "WHO NEVER DESERVED ACCESS"',
        "mood": "mindset",
    },
    {
        "name": "DARK_TRUTH",
        "desc": "3 harsh truths. Each line cuts deeper than the last.",
        "example": '"THEY CLAP FOR YOU" / "WHEN YOU ARE USEFUL" / "NOT WHEN YOU ARE STRUGGLING"',
        "mood": "dark_truth",
    },
    {
        "name": "ANIMAL_POWER",
        "desc": "2–3 lines. Each animal represents a trait. Keep it visual and dominant.",
        "example": '"CALM LIKE A LION" / "WATCHFUL LIKE AN EAGLE" / "STRIKE WITHOUT WARNING"',
        "mood": "attitude",
    },
    {
        "name": "NEVER_DO",
        "desc": "4 rules. Each line is a hard boundary. No explanation tone.",
        "example": '"DO NOT EXPLAIN YOUR VALUE" / "TO PEOPLE WHO QUESTION IT" / "DO NOT CHASE ATTENTION" / "MOVE IN SILENCE"',
        "mood": "attitude",
    },
]

BANNED_WORDS = [
    "never give up", "keep going", "believe in yourself",
    "work hard", "hustle", "grind", "stay positive",
    "dream big", "you got this", "seize the day",
    "rise and shine", "be the best",
]

REPLACEMENT_STYLES = {
    "keep going": "keep moving in silence",
    "believe in yourself": "trust your decisions",
    "work hard": "outlast everyone quietly",
    "stay positive": "stay controlled",
    "dream big": "build something real",
}

STAT_PATTERN = re.compile(r'\b\d+\s*%|\b\d+\s*percent', re.IGNORECASE)

# ── Comprehensive character replacement map ───────────────────
_CHAR_MAP = {
    # Apostrophes / single quotes
    "\u0027": "",   # ' standard apostrophe
    "\u2018": "",   # ' left single quotation mark
    "\u2019": "",   # ' right single quotation mark (most common culprit)
    "\u201a": "",   # ‚ single low-9 quotation mark
    "\u201b": "",   # ‛ single high-reversed-9
    "\u0060": "",   # ` backtick
    "\u00b4": "",   # ´ acute accent used as apostrophe
    "\uff07": "",   # ＇ fullwidth apostrophe

    # Dashes & hyphens
    "\u2013": " ",  # – en dash
    "\u2014": " ",  # — em dash
    "\u2015": " ",  # ― horizontal bar
    "\u2012": " ",  # ‒ figure dash
    "\u2011": "",   # ‑ non-breaking hyphen
    "\u00ad": "",   # ­ soft hyphen
    "\ufe58": " ",  # ﹘ small em dash
    "\ufe63": " ",  # ﹣ small hyphen-minus
    "\uff0d": " ",  # － fullwidth hyphen-minus
    "\u002d": "",   # - standard hyphen-minus

    # Ellipsis
    "\u2026": "",   # … horizontal ellipsis
    "\u22ef": "",   # ⋯ midline ellipsis

    # Brackets & braces
    "\u0028": "",   # ( left parenthesis
    "\u0029": "",   # ) right parenthesis
    "\u005b": "",   # [ left square bracket
    "\u005d": "",   # ] right square bracket
    "\u007b": "",   # { left curly brace
    "\u007d": "",   # } right curly brace
    "\uff08": "",   # （ fullwidth left parenthesis
    "\uff09": "",   # ） fullwidth right parenthesis
    "\u27e8": "",   # ⟨ mathematical left angle bracket
    "\u27e9": "",   # ⟩ mathematical right angle bracket
    "\u3008": "",   # 〈 left angle bracket
    "\u3009": "",   # 〉 right angle bracket
    "\u300a": "",   # 《 left double angle bracket
    "\u300b": "",   # 》 right double angle bracket

    # Slashes & backslashes
    "\u005c": "",   # \ backslash (JSON escape char)
    "\u002f": "",   # / forward slash
    "\u2044": "",   # ⁄ fraction slash

    # Newlines / tabs / control chars → space
    "\u000a": " ",  # \n newline
    "\u000d": " ",  # \r carriage return
    "\u0009": " ",  # \t tab
    "\u000b": " ",  # vertical tab
    "\u000c": " ",  # form feed
    "\u0085": " ",  # next line
    "\u2028": " ",  # line separator
    "\u2029": " ",  # paragraph separator

    # Colons & semicolons
    "\u003a": "",   # : colon
    "\u003b": "",   # ; semicolon
    "\uff1a": "",   # ： fullwidth colon
    "\uff1b": "",   # ； fullwidth semicolon

    # Other punctuation
    "\u0021": "",   # ! exclamation mark
    "\u003f": "",   # ? question mark
    "\u002c": "",   # , comma
    "\u002e": "",   # . period
    "\u2022": "",   # • bullet
    "\u00b7": "",   # · middle dot
    "\u2023": "",   # ‣ triangular bullet
    "\u25cf": "",   # ● black circle
    "\u00a0": " ",  # non-breaking space → regular space
    "\u200b": "",   # zero-width space
    "\u200c": "",   # zero-width non-joiner
    "\u200d": "",   # zero-width joiner
    "\ufeff": "",   # BOM / zero-width no-break space
    "\u00ab": "",   # « left-pointing double angle quotation mark
    "\u00bb": "",   # » right-pointing double angle quotation mark
    "\u2039": "",   # ‹ single left-pointing angle quotation mark
    "\u203a": "",   # › single right-pointing angle quotation mark
    "\u0023": "",   # # hash
    "\u0040": "",   # @ at sign
    "\u0026": "",   # & ampersand
    "\u002a": "",   # * asterisk
    "\u005e": "",   # ^ caret
    "\u007e": "",   # ~ tilde
    "\u007c": "",   # | pipe
    "\u003c": "",   # < less than
    "\u003e": "",   # > greater than
    "\u003d": "",   # = equals
    "\u002b": "",   # + plus
    "\u005f": " ",  # _ underscore → space
}


def _sanitize_phrase_text(text: str) -> str:
    if not text:
        return text
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    for char, replacement in _CHAR_MAP.items():
        text = text.replace(char, replacement)
    text = text.encode("ascii", errors="ignore").decode("ascii")
    text = text.replace('"', "")
    text = re.sub(r" {2,}", " ", text).strip()
    return text


def _sanitize_raw_json(raw: str) -> str:
    raw = raw.replace("\u2018", "'").replace("\u2019", "'")
    raw = raw.replace("\u201c", '"').replace("\u201d", '"')
    raw = raw.replace("\u201a", "'").replace("\u201b", "'")
    raw = raw.replace("\u2013", " ").replace("\u2014", " ")
    raw = raw.replace("\u2015", " ").replace("\u2012", " ")
    raw = raw.replace("\u2026", "...")
    raw = raw.replace("\u00a0", " ").replace("\u200b", "").replace("\ufeff", "")
    raw = re.sub(r'(?<=[^\\])\n', ' ', raw)
    raw = re.sub(r"```(?:json)?\s*", "", raw).strip().replace("```", "")
    raw = re.sub(r",\s*([}\]])", r"\1", raw)
    return raw


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
    raw = _sanitize_raw_json(raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    start = raw.find('{')
    if start == -1:
        raise ValueError(f"No JSON object found:\n{raw[:200]}")
    depth = 0
    for i, ch in enumerate(raw[start:], start):
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return json.loads(raw[start:i+1])
    raise ValueError(f"Unclosed JSON object:\n{raw[:200]}")


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


def generate_content() -> dict:
    """
    Generate phrase-by-phrase quote with natural splits.
    - JSON parse errors retry instead of crashing.
    - All phrase text sanitized post-parse.
    """
    theme     = _pick_theme()
    audience  = TARGET_AUDIENCE
    structure = random.choice(QUOTE_STRUCTURES)

    log.info(f"Audience: {audience} | Structure: {structure['name']} | Theme: {theme[:55]}...")

    # ── REWRITTEN PROMPT ─────────────────────────────────────────────────────
    prompt = f"""You write viral attitude content for YouTube Shorts.

CHANNEL: "{CHANNEL_NAME}"
AUDIENCE: {AUDIENCE_AGE_GROUP}
TONE: {AUDIENCE_STYLE}
TOPIC: {theme}
STRUCTURE: {structure['name']} — {structure['desc']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WHAT MAKES A PHRASE HIT HARD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Every phrase must feel like a realisation the viewer already
knew but never had words for. It should make them pause,
reread it, and want to screenshot it.

Ask yourself before writing each phrase:
  → Would a 22-year-old send this to their best friend at 2am?
  → Does it reveal something true that most people are afraid to say?
  → Does it feel earned — not preachy, not obvious?

GREAT phrases expose a hidden truth with zero filler:
  "THEY CELEBRATE YOUR WINS" / "NEVER YOUR BECOMING"
  "SILENCE IS NOT WEAKNESS" / "IT IS CONTROLLED POWER"
  "A WOLF DOES NOT LOSE SLEEP" / "OVER OPINIONS OF SHEEP"
  "STOP EXPLAINING YOURSELF" / "TO PEOPLE WHO MISREAD YOU ON PURPOSE"

WEAK phrases are vague, preachy, or could appear on any poster:
  BAD: "BELIEVE IN YOUR JOURNEY"        — says nothing specific
  BAD: "STAY FOCUSED ON YOUR GOALS"     — generic, zero punch
  BAD: "SUCCESS REQUIRES SACRIFICE"     — cliche, heard 1000 times
  BAD: "YOU HAVE THE POWER WITHIN YOU"  — empty motivation

The difference: GREAT phrases name a SPECIFIC feeling or situation.
WEAK phrases state obvious advice nobody asked for.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHRASE CONSTRUCTION RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. 3 to 5 phrases total. 3 to 7 words per phrase.
2. Each phrase = one complete, standalone idea. Never cut mid-thought.
3. Phrases must BUILD — each one sharpens or flips the one before it.
4. The FINAL phrase is the gut-punch. It reframes everything before it.
5. Use SPECIFIC nouns and verbs. Avoid vague words: things, people,
   journey, path, way, life, world, power, energy, force.
6. Use tension — set up an expectation, then break it in the next phrase.

Follow this structure for {structure['name']}:
{structure['example']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HARD BANS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
— No percentages or statistics
— No: hustle, grind, dream big, believe in yourself, never give up,
       journey, path, potential, mindset shift, level up, next chapter,
       unleash, inner, greatness, empower, limitless, transform
— No relationship advice — self-mastery and observation only
— No punctuation of any kind in phrase text:
  Write DONT not DON'T  |  WONT not WON'T  |  ITS not IT'S
— Plain capital letters A-Z and spaces ONLY in phrase text

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
  "description": "Two sentences expanding on the quote. No hashtags. No percentages."
}}

highlight = the single word in that phrase carrying the most emotional weight.
title = written like a human wrote it for someone they know — not an ad.
"""
    # ─────────────────────────────────────────────────────────────────────────

    data       = None
    last_error = None

    for attempt in range(3):
        try:
            raw  = _call_groq(prompt, temperature=0.90 + attempt * 0.03)
            data = _parse_json(raw)
        except (ValueError, json.JSONDecodeError) as exc:
            last_error = exc
            log.warning(f"Attempt {attempt+1}: JSON parse failed ({exc}) — retrying")
            continue

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

    if data is None:
        raise ValueError(f"All 3 attempts produced invalid JSON. Last error: {last_error}")

    if "phrases" not in data or len(data.get("phrases", [])) < 2:
        raise ValueError("Not enough phrases generated")
    for field in ["mood", "title"]:
        if field not in data or not str(data[field]).strip():
            raise ValueError(f"Missing field: '{field}'")

    if data["mood"] not in ["attitude", "dark_truth", "mindset"]:
        data["mood"] = structure.get("mood", "attitude")

    data["phrases"] = data["phrases"][:MAX_PHRASES]

    cleaned = []
    for p in data["phrases"]:
        text      = _sanitize_phrase_text(str(p.get("text", "")))
        highlight = _sanitize_phrase_text(str(p.get("highlight", "")))
        if not text:
            continue
        text = STAT_PATTERN.sub("many", text)
        words = text.split()
        if len(words) > 7:
            text = " ".join(words[:6])
        if not highlight or highlight.upper() not in text.upper():
            highlight = text.split()[-1]
        cleaned.append({"text": text, "highlight": highlight.upper()})

    if len(cleaned) < 2:
        raise ValueError("Not enough valid phrases after cleaning")

    data["phrases"]     = cleaned
    data["description"] = _sanitize_phrase_text(data.get("description", "") or "")
    data["description"] = data["description"] or " ".join(p["text"] for p in cleaned)
    data["content"]     = " ".join(p["text"] for p in cleaned)
    data["hook"]        = cleaned[0]["text"]
    data["answer"]      = cleaned[-1]["text"]
    data["audience"]    = audience
    data["structure"]   = structure["name"]

    log.info(f"Generated | mood={data['mood']} | {len(cleaned)} phrases | {structure['name']}")
    for i, p in enumerate(cleaned):
        log.info(f"  [{i+1}] {p['text']}  (yellow: {p['highlight']})")

    return data
