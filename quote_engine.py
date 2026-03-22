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
# Every character that could break JSON string values or rendering.
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
    """
    Strip every character that could break JSON or rendering from a phrase string.
    Applied to phrase text and highlight values AFTER JSON is parsed.
    Safe to call multiple times — idempotent.
    """
    if not text:
        return text

    # 1. Unicode normalization — decompose then strip combining marks
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))

    # 2. Apply full character replacement map
    for char, replacement in _CHAR_MAP.items():
        text = text.replace(char, replacement)

    # 3. Remove any remaining non-ASCII characters
    text = text.encode("ascii", errors="ignore").decode("ascii")

    # 4. Remove any double quotes left inside the value
    text = text.replace('"', "")

    # 5. Collapse multiple spaces → single space, strip edges
    text = re.sub(r" {2,}", " ", text).strip()

    return text


def _sanitize_raw_json(raw: str) -> str:
    """
    Fix common issues in the raw JSON string BEFORE parsing.
    Only touches characters safe to replace globally
    (not structural JSON chars like { } [ ] " : ,).
    """
    # Smart / curly quotes → straight quotes (structural fix for JSON)
    raw = raw.replace("\u2018", "'").replace("\u2019", "'")
    raw = raw.replace("\u201c", '"').replace("\u201d", '"')
    raw = raw.replace("\u201a", "'").replace("\u201b", "'")

    # Dashes in string values
    raw = raw.replace("\u2013", " ").replace("\u2014", " ")
    raw = raw.replace("\u2015", " ").replace("\u2012", " ")

    # Ellipsis
    raw = raw.replace("\u2026", "...")

    # Non-breaking / zero-width spaces
    raw = raw.replace("\u00a0", " ").replace("\u200b", "").replace("\ufeff", "")

    # Literal newlines inside string values → space
    raw = re.sub(r'(?<=[^\\])\n', ' ', raw)

    # Remove markdown code fences
    raw = re.sub(r"```(?:json)?\s*", "", raw).strip().replace("```", "")

    # Remove trailing commas before } or ] which break JSON
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
    # Fallback: extract outermost { ... } block
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
    - All phrase text sanitized post-parse to remove every
      character that could cause downstream issues.
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
8. Phrase text must use ONLY plain capital letters A-Z and spaces.
   No apostrophes, commas, periods, dashes, hyphens, brackets, colons,
   exclamation marks, question marks, or ANY punctuation whatsoever.
   Write DONT not DON'T. YOURE not YOU'RE. WONT not WON'T. ITS not IT'S.

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

    # ── Sanitize all phrase text and highlight values ─────────
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
