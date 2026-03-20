# quote_engine.py
# ============================================================
# Generates content using Groq AI.
#
# Theme selection priority:
#   1. If .logs/next_week_ideas.json exists and is valid
#      → use Groq-generated ideas from last week's analytics
#   2. Otherwise → use default CONTENT_THEMES from config.py
#
# This creates the feedback loop:
#   Analytics → Groq generates ideas → pipeline uses them
# ============================================================

import json
import logging
import os
import random
import re
import datetime
import httpx
from groq import Groq
from tenacity import (
    retry, stop_after_attempt, wait_exponential, before_sleep_log
)
from config import GROQ_API_KEY, CONTENT_THEMES, CHANNEL_NAME, LOGS_DIR

log = logging.getLogger("QuoteEngine")
GROQ_MODEL = "llama-3.1-8b-instant"
_CLIENT    = None


def _init_groq() -> Groq:
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT
    if not GROQ_API_KEY:
        raise ValueError(
            "GROQ_API_KEY is not set.\n"
            "Add it to GitHub Secrets: Settings → Secrets → GROQ_API_KEY"
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
        model    = GROQ_MODEL,
        messages = [{"role": "user", "content": prompt}],
        temperature = temperature,
    )
    return resp.choices[0].message.content.strip()


def _load_analytics_ideas() -> list:
    """
    Load Groq-generated content ideas from last week's analytics.
    Returns empty list if no valid ideas file exists.
    """
    ideas_file = LOGS_DIR / "next_week_ideas.json"
    if not ideas_file.exists():
        log.info("No analytics ideas file found — using default themes")
        return []
    try:
        data       = json.loads(ideas_file.read_text(encoding="utf-8"))
        valid_until = datetime.date.fromisoformat(data.get("valid_until", "2000-01-01"))
        if valid_until < datetime.date.today():
            log.info("Analytics ideas expired — using default themes")
            return []
        ideas = data.get("ideas", [])
        if ideas:
            log.info(f"Using {len(ideas)} analytics-generated content ideas")
        return ideas
    except Exception as exc:
        log.warning(f"Could not load analytics ideas: {exc} — using defaults")
        return []


def _pick_theme() -> str:
    """
    Pick a content theme.
    Priority: analytics-generated ideas > default config themes.
    """
    analytics_ideas = _load_analytics_ideas()
    if analytics_ideas:
        return random.choice(analytics_ideas)
    return random.choice(CONTENT_THEMES)


def generate_content() -> dict:
    """
    Generate one complete piece of content for a Shorts video.

    Returns dict with:
      content     — text shown on screen (punchy, under 200 chars)
      mood        — visual theme: dark_truth | wealth_fact | mindset
      title       — YouTube title (60-70 chars, click-stopping hook)
      description — YouTube description expansion
    """
    theme = _pick_theme()
    log.info(f"Theme: {theme[:70]}...")

    prompt = f"""You create viral content for a YouTube Shorts channel called "{CHANNEL_NAME} 😎".
Niche: Raw masculine mindset, silent strength, brutal self-improvement truths.
Target: Men aged 16-35 globally who want to become better.

Content angle: {theme}

VIDEO FORMAT: 27 seconds, bold text on dark cinematic background, no voiceover.
So the TEXT on screen must do ALL the work — it must be impossible to scroll past.

Return ONLY a valid JSON object, no markdown, no code blocks, no extra text:
{{
  "content": "The text shown on screen. RULES: max 180 characters. 1-2 short punchy sentences. Use simple words (6th grade level). Must include either a number/statistic OR a powerful contrast (e.g. 'most men... the few who...'). No hashtags. No quotation marks inside.",
  "mood": "EXACTLY ONE of: dark_truth | wealth_fact | mindset",
  "title": "YouTube title. 55-65 chars. Must have a hook in first 4 words. Include 1 relevant emoji. Make it impossible NOT to click. Examples of good hooks: 'Why most men...', 'The truth about...', 'Nobody tells you...'",
  "description": "2 sentences that expand the content. Adds value. No hashtags here."
}}

RULES:
- content must be SPECIFIC and PERSONAL — it should feel like it was written about the viewer
- Avoid clichés: no 'rise and grind', 'hustle', 'beast mode'
- mood must be EXACTLY: dark_truth, wealth_fact, or mindset
- title must create CURIOSITY or FEAR OF MISSING OUT
- Return ONLY the JSON, nothing else"""

    raw = _call_groq(prompt, temperature=0.9)

    # Strip markdown code fences if Groq added them
    raw = re.sub(r"```(?:json)?\s*", "", raw).strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
        else:
            raise ValueError(f"Groq returned invalid JSON:\n{raw[:300]}")

    for field in ["content", "mood", "title"]:
        if field not in data or not data[field]:
            raise ValueError(f"Groq response missing field: '{field}'")

    # description is optional — use fallback if missing
    if not data.get("description"):
        data["description"] = data.get("content", "")

    # Sanitize mood
    if data["mood"] not in ["dark_truth", "wealth_fact", "mindset"]:
        log.warning(f"Invalid mood '{data['mood']}' — defaulting to 'dark_truth'")
        data["mood"] = "dark_truth"

    # Trim content if too long
    if len(data["content"]) > 200:
        data["content"] = data["content"][:197] + "..."

    log.info(f"Generated | mood={data['mood']} | title={data['title'][:55]}...")
    return data
