# quote_engine.py
# ============================================================
# Generates viral attitude/mindset content using Groq AI.
#
# Content philosophy:
#   HOOK   — Universal truth that makes someone stop mid-scroll.
#            Works on the largest section of viewers because it
#            speaks to something EVERY person has felt.
#            Feels like someone finally said what everyone thinks.
#
#   ANSWER — A revelation that reframes how they see themselves.
#            Not advice. Not motivation. A shift in perspective
#            that makes them think "I never looked at it that way."
#            The "wahhh" moment.
#
# 15-second structure:
#   Hook (5s) → Answer (7s) → Outro (3s)
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
)

log        = logging.getLogger("QuoteEngine")
GROQ_MODEL = "llama-3.1-8b-instant"
_CLIENT    = None

# ── Banned phrases — clichés that make viewers feel nothing ──
BANNED_PHRASES = [
    "never give up", "keep going", "believe in yourself",
    "success takes time", "work hard", "hustle", "grind",
    "dream big", "stay focused", "you got this", "be the best",
    "push harder", "rise and shine", "seize the day",
    "winners never quit", "think positive",
]


def _init_groq() -> Groq:
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not set. Add to GitHub Secrets.")
    http    = httpx.Client(timeout=60.0, trust_env=False)
    _CLIENT = Groq(api_key=GROQ_API_KEY, http_client=http)
    return _CLIENT


@retry(
    reraise=True,
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    before_sleep=before_sleep_log(log, logging.WARNING),
)
def _call_groq(prompt: str, temperature: float = 0.92) -> str:
    client = _init_groq()
    resp   = client.chat.completions.create(
        model       = GROQ_MODEL,
        messages    = [{"role": "user", "content": prompt}],
        temperature = temperature,
    )
    return resp.choices[0].message.content.strip()


def _parse_json(raw: str) -> dict:
    """Extract first valid JSON object from Groq response."""
    raw = re.sub(r"```(?:json)?\s*", "", raw).strip().replace("```", "")

    # Try direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Find first complete { ... } by counting brace depth
    start = raw.find('{')
    if start == -1:
        raise ValueError(f"No JSON in response:\n{raw[:200]}")

    depth = 0
    for i, ch in enumerate(raw[start:], start):
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(raw[start:i+1])
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSON:\n{raw[start:i+1][:200]}") from exc

    raise ValueError(f"Unclosed JSON in response:\n{raw[:200]}")


def _contains_banned(text: str) -> bool:
    t = text.lower()
    return any(b in t for b in BANNED_PHRASES)


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
    Generate 15-second video content.

    Returns dict with:
      hook    — 5s opening. Stops the scroll. Universal truth.
      answer  — 7s revelation. Reframes how viewer sees themselves.
      mood    — dark_truth | wealth_fact | mindset
      title   — YouTube title
      description — 2 sentences
      audience, content (backward compat)
    """
    theme    = _pick_theme()
    audience = TARGET_AUDIENCE
    log.info(f"Audience: {audience} | Theme: {theme[:65]}...")

    prompt = f"""You write viral YouTube Shorts content for "{CHANNEL_NAME}".

AUDIENCE: {AUDIENCE_AGE_GROUP}
TONE: {AUDIENCE_STYLE}
TOPIC ANGLE: {theme}

THE FORMAT IS 15 SECONDS:
- Hook shows for 5 seconds
- Answer shows for 7 seconds
- No voiceover. Just bold text on cinematic background.

YOUR MISSION:
Write content that makes someone STOP scrolling in the first 0.5 seconds
and leave the video thinking differently about themselves.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOOK — what the viewer reads first (5 seconds on screen)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The hook must work on the LARGEST possible audience.
Use universal human experiences — things EVERYONE has felt:
  - Being judged before being understood
  - Feeling stuck while watching others move
  - Working hard but feeling invisible
  - Being underestimated by people who don't know your story
  - Staying quiet while others get the credit

The hook should make someone think: "How did they know exactly how I feel?"

HOOK RULES:
- Max 80 characters
- Must be a COMPLETE thought that hits like a punch
- Short words. Hard impact. No explanation needed.
- NOT a question. NOT "most men...". NOT a fake stat.
- Reads like something you'd write on a wall.
- FORBIDDEN words: never give up, hustle, grind, work hard, believe in yourself

GREAT HOOK EXAMPLES:
  "The people who doubted you are watching your every move."
  "You're not behind. You're just building in silence."
  "The strongest people rarely look strong."
  "Nobody claps for you in the beginning. That's the point."
  "They called you too sensitive. You call it self-aware."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ANSWER — the revelation (7 seconds on screen)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The answer must REFRAME how the viewer sees themselves.
Not advice. Not motivation. A shift in perspective.
The viewer should think: "I never looked at it that way."

This is the "wahhh" moment — when something clicks.
It should feel like a mentor finally telling you the truth.

ANSWER RULES:
- Max 150 characters
- Must change the viewer's perspective on the hook
- Specific, not generic. Unexpected, not obvious.
- FORBIDDEN: never give up, keep going, you got this, stay focused
- Should feel EARNED — like you had to live something to know it

GREAT ANSWER EXAMPLES (paired with hooks above):
  Hook: "The people who doubted you are watching your every move."
  Answer: "So every day you show up is a statement. Not to them. To yourself."

  Hook: "You're not behind. You're just building in silence."
  Answer: "The men who moved fast are already forgotten. The patient ones built something that lasted."

  Hook: "Nobody claps for you in the beginning. That's the point."
  Answer: "The work you do when no one is watching decides who you become when everyone is."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Return ONLY valid JSON, nothing else before or after:
{{
  "hook": "max 80 chars. Universal truth. Stops the scroll.",
  "answer": "max 150 chars. Revelation. Reframes how they see themselves.",
  "mood": "EXACTLY ONE of: dark_truth | wealth_fact | mindset",
  "title": "YouTube title. 50-60 chars. Hooks first 4 words. 1 emoji.",
  "description": "2 sentences expanding the content. No hashtags."
}}"""

    # Try up to 3 times to get content without banned phrases
    for attempt in range(3):
        raw  = _call_groq(prompt, temperature=0.92 + attempt * 0.02)
        data = _parse_json(raw)

        # Validate fields
        for field in ["hook", "answer", "mood", "title"]:
            if field not in data or not str(data[field]).strip():
                raise ValueError(f"Missing field: '{field}'")

        # Check for banned phrases
        if _contains_banned(data.get("hook", "")) or _contains_banned(data.get("answer", "")):
            log.warning(f"Attempt {attempt+1}: banned phrase detected — retrying")
            if attempt < 2:
                continue
            # Accept on last attempt even if not perfect
            log.warning("Accepting content despite banned phrase on final attempt")

        break

    # Defaults
    if not data.get("description"):
        data["description"] = data["answer"]

    # Sanitize mood
    if data["mood"] not in ["dark_truth", "wealth_fact", "mindset"]:
        data["mood"] = "dark_truth"

    # Enforce length limits
    if len(data["hook"]) > 90:
        data["hook"] = data["hook"][:87] + "..."
    if len(data["answer"]) > 165:
        data["answer"] = data["answer"][:162] + "..."

    # Backward compat
    data["audience"] = audience
    data["content"]  = data["answer"]

    log.info(f"Generated | mood={data['mood']} | audience={audience}")
    log.info(f"  Hook:   {data['hook']}")
    log.info(f"  Answer: {data['answer']}")
    log.info(f"  Title:  {data['title']}")
    return data
