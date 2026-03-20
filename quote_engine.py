# quote_engine.py
# ============================================================
# Generates content using Groq AI — audience-aware.
#
# Returns hook + answer separately (new video structure):
#   hook   → shown first 8 seconds (open loop)
#   answer → shown next 10 seconds (the reveal)
#   comment_question → shown 3 seconds (engagement)
#
# Audience priority:
#   1. Analytics ideas from .logs/next_week_ideas.json (if valid)
#   2. Audience-specific themes from config.py
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
    AUDIENCE_STYLE, AUDIENCE_HOOK_STYLE, AUDIENCE_AGE_GROUP,
)

log        = logging.getLogger("QuoteEngine")
GROQ_MODEL = "llama-3.1-8b-instant"
_CLIENT    = None


def _init_groq() -> Groq:
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT
    if not GROQ_API_KEY:
        raise ValueError(
            "GROQ_API_KEY is not set.\n"
            "Add it to GitHub Secrets: GROQ_API_KEY"
        )
    http    = httpx.Client(timeout=60.0, trust_env=False)
    _CLIENT = Groq(api_key=GROQ_API_KEY, http_client=http)
    return _CLIENT


@retry(
    reraise=True,
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    before_sleep=before_sleep_log(log, logging.WARNING),
)
def _call_groq(prompt: str, temperature: float = 0.9) -> str:
    client = _init_groq()
    resp   = client.chat.completions.create(
        model       = GROQ_MODEL,
        messages    = [{"role": "user", "content": prompt}],
        temperature = temperature,
    )
    return resp.choices[0].message.content.strip()


def _load_analytics_ideas() -> list:
    """Load Groq-generated ideas from last Sunday's analytics report."""
    f = LOGS_DIR / "next_week_ideas.json"
    if not f.exists():
        log.info("No analytics ideas — using default themes")
        return []
    try:
        data        = json.loads(f.read_text(encoding="utf-8"))
        valid_until = datetime.date.fromisoformat(data.get("valid_until", "2000-01-01"))
        if valid_until < datetime.date.today():
            log.info("Analytics ideas expired — using default themes")
            return []
        ideas = data.get("ideas", [])
        if ideas:
            log.info(f"Using {len(ideas)} analytics-generated ideas")
        return ideas
    except Exception as exc:
        log.warning(f"Could not load analytics ideas: {exc} — using defaults")
        return []


def _pick_theme() -> str:
    """Analytics ideas first, then audience-specific themes."""
    ideas = _load_analytics_ideas()
    pool  = ideas if ideas else CONTENT_THEMES
    return random.choice(pool)


def generate_content() -> dict:
    """
    Generate complete content for one video.

    Returns dict with:
      hook             — 8s opening text (creates open loop, max 120 chars)
      answer           — 10s reveal text (the brutal truth, max 180 chars)
      comment_question — 3s engagement question (max 80 chars)
      mood             — dark_truth | wealth_fact | mindset
      title            — YouTube title (55-65 chars)
      description      — YouTube description (2 sentences)
      audience         — which audience this was generated for
    """
    theme    = _pick_theme()
    audience = TARGET_AUDIENCE
    log.info(f"Audience: {audience} | Theme: {theme[:65]}...")

    prompt = f"""You create viral YouTube Shorts content for "{CHANNEL_NAME} 😎".

AUDIENCE: {AUDIENCE_AGE_GROUP}
TONE: {AUDIENCE_STYLE}
HOOK STYLE: {AUDIENCE_HOOK_STYLE}
CONTENT ANGLE: {theme}

VIDEO FORMAT:
- 27 seconds total, NO voiceover, bold text on cinematic background
- Viewer sees the HOOK for 8 seconds first (creates curiosity/open loop)
- Then the ANSWER appears for 10 seconds (the devastating reveal)
- Then a QUESTION for 3 seconds (makes them comment)
- The hook must make the answer IMPOSSIBLE to skip

CRITICAL RULES:
- hook: max 120 characters. Must be an incomplete truth or shocking statement
  that creates an OPEN LOOP — viewer NEEDS to see the answer.
  DO NOT complete the thought. Leave them hanging.
  Good: "97% of men will never be great." (why? they need to know)
  Good: "The one habit separating winners from losers isn't discipline."
  Bad: "Work hard and you will succeed." (complete thought, no reason to stay)
- answer: max 180 characters. The brutal reveal. Simple words, maximum impact.
  Must feel like a punch to the chest. 6th grade reading level.
- comment_question: max 80 chars. A polarising question they MUST answer.
  Examples: "Which one are you?", "What's stopping you?", "Agree?"
- title: 55-65 chars. Hook in first 4 words. 1 emoji. Impossible not to click.
- description: 2 sentences expanding the content. No hashtags.

Return ONLY valid JSON, no markdown, no code blocks:
{{
  "hook": "...",
  "answer": "...",
  "comment_question": "...",
  "mood": "EXACTLY ONE of: dark_truth | wealth_fact | mindset",
  "title": "...",
  "description": "..."
}}"""

    raw = _call_groq(prompt, temperature=0.9)
    raw = re.sub(r"```(?:json)?\s*", "", raw).strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Find the first complete JSON object only
        match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', raw, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError:
                # Last resort — find content between first { and last }
                start = raw.find('{')
                end   = raw.rfind('}') + 1
                if start != -1 and end > start:
                    data = json.loads(raw[start:end])
                else:
                    raise ValueError(f"Groq returned invalid JSON:\n{raw[:300]}")
        else:
            raise ValueError(f"Groq returned invalid JSON:\n{raw[:300]}")


    # Validate required fields
    for field in ["hook", "answer", "comment_question", "mood", "title"]:
        if field not in data or not data[field]:
            raise ValueError(f"Groq response missing field: '{field}'")

    # description is optional
    if not data.get("description"):
        data["description"] = data["answer"]

    # Sanitize mood
    if data["mood"] not in ["dark_truth", "wealth_fact", "mindset"]:
        log.warning(f"Invalid mood '{data['mood']}' — defaulting to 'dark_truth'")
        data["mood"] = "dark_truth"

    # Enforce length limits
    if len(data["hook"]) > 130:
        data["hook"] = data["hook"][:127] + "..."
    if len(data["answer"]) > 200:
        data["answer"] = data["answer"][:197] + "..."
    if len(data["comment_question"]) > 90:
        data["comment_question"] = data["comment_question"][:87] + "..."

    # Add audience tag and backward-compatible content field
    data["audience"] = audience
    data["content"]  = data["answer"]   # used by youtube_uploader description

    log.info(f"Generated | mood={data['mood']} | audience={audience}")
    log.info(f"  Hook:   {data['hook'][:70]}...")
    log.info(f"  Answer: {data['answer'][:70]}...")
    log.info(f"  Title:  {data['title']}")
    return data
