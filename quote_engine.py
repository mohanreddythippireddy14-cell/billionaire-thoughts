# quote_engine.py
# ============================================================
# Generates finance content using Groq AI (free tier)
# Returns content + visual mood + YouTube title + description
# ============================================================

import json
import logging
import random
import re
import httpx
from groq import Groq
from tenacity import (
    retry, stop_after_attempt, wait_exponential, before_sleep_log
)
from config import GROQ_API_KEY, CONTENT_THEMES, CHANNEL_NAME, CHANNEL_EMOJI

log = logging.getLogger("QuoteEngine")
GROQ_MODEL = "llama-3.1-8b-instant"   # Free, fast, good quality
_CLIENT    = None                       # Cached Groq client


def _init_groq() -> Groq:
    """Create Groq client once and reuse it."""
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT
    if not GROQ_API_KEY:
        raise ValueError(
            "GROQ_API_KEY is not set.\n"
            "Add it to GitHub Secrets: Settings → Secrets → GROQ_API_KEY"
        )
    # trust_env=False bypasses broken system proxy settings
    http = httpx.Client(timeout=60.0, trust_env=False)
    _CLIENT = Groq(api_key=GROQ_API_KEY, http_client=http)
    return _CLIENT


@retry(
    reraise=True,
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    before_sleep=before_sleep_log(log, logging.WARNING),
)
def _call_groq(prompt: str, temperature: float = 0.9) -> str:
    """Call Groq API with automatic retry on failure."""
    client = _init_groq()
    resp = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    return resp.choices[0].message.content.strip()


def generate_content() -> dict:
    """
    Generate one complete piece of finance content for a Shorts video.

    Returns a dict with:
      content   — text displayed on screen (2–3 punchy sentences, under 220 chars)
      mood      — visual theme: 'dark_truth', 'wealth_fact', or 'mindset'
      title     — YouTube title (attention-grabbing, 60–70 chars, 1 emoji)
      description — YouTube description expansion (2–3 sentences)
    """
    theme = random.choice(CONTENT_THEMES)

    prompt = f"""You create content for a YouTube Shorts finance channel called "{CHANNEL_NAME} {CHANNEL_EMOJI}".
Target audience: global English speakers aged 18–35 who want to build wealth.

Generate content about: {theme}

Return ONLY a valid JSON object — no markdown, no code blocks, no extra text:
{{
  "content": "2-3 punchy sentences shown on screen. Under 220 characters total. Must include a specific number, stat, or contrast. No hashtags. No quotation marks inside.",
  "mood": "EXACTLY ONE of: dark_truth | wealth_fact | mindset",
  "title": "YouTube title. 60-70 chars. Hook the viewer in the first 4 words. Include 1 emoji. Make it impossible NOT to click.",
  "description": "2-3 sentences that expand on the content for YouTube description."
}}

Rules:
- content must be SHOCKING and SPECIFIC — not generic advice
- Use real numbers: '83% of millionaires...', '7 income streams', '$1M in 10 years'
- mood must be EXACTLY: dark_truth, wealth_fact, or mindset
- title must make someone stop mid-scroll
- Return ONLY the JSON object"""

    raw = _call_groq(prompt, temperature=0.9)

    # Strip markdown code fences if Groq added them
    raw = re.sub(r"```(?:json)?\s*", "", raw).strip()

    # Parse JSON
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Try to extract JSON from surrounding text
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
        else:
            raise ValueError(
                f"Groq returned invalid JSON. First 300 chars:\n{raw[:300]}"
            )

    # Validate required fields
    for field in ["content", "mood", "title", "description"]:
        if field not in data or not data[field]:
            raise ValueError(f"Groq response missing field: '{field}'")

    # Sanitize mood — must be one of the three valid values
    if data["mood"] not in ["dark_truth", "wealth_fact", "mindset"]:
        log.warning(f"Invalid mood '{data['mood']}' — defaulting to 'wealth_fact'")
        data["mood"] = "wealth_fact"

    # Trim content if too long
    if len(data["content"]) > 240:
        data["content"] = data["content"][:237] + "..."

    log.info(f"Content generated | mood={data['mood']} | title={data['title'][:55]}...")
    return data
