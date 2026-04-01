# quote_engine.py — v3 Brutal Truth Engine (No Punctuation Mode)

import random
import re
import logging

log = logging.getLogger("QuoteEngine")

MAX_PHRASES = 4

# ─────────────────────────────────────────────
# CORE GENERATION (STATIC BASE FOR NOW)
# Replace later with Groq if needed
# ─────────────────────────────────────────────

HOOKS = [
    "YOU THINK YOU ARE BROKE",
    "YOUR SALARY IS NOT THE PROBLEM",
    "YOU WAIT FOR SALARY DAY",
    "YOU EARN BUT STILL FEEL STUCK",
    "YOU CHECK YOUR BALANCE EVERY DAY",
]

SCENARIOS = [
    "BUT YOUR MONEY DISAPPEARS IN DAYS",
    "AND STILL DONT KNOW WHERE IT WENT",
    "BUT NOTHING ACTUALLY CHANGES",
    "AND YOU REPEAT THE SAME MONTH AGAIN",
    "BUT YOUR ACCOUNT LOOKS THE SAME",
]

PAYOFFS = [
    "YOU JUST DONT TRACK IT",
    "YOU ARE NOT BROKE YOU ARE UNCONTROLLED",
    "YOUR HABITS ARE COSTING YOU",
    "YOU CALL IT LOW INCOME IT IS NO SYSTEM",
    "MONEY LEAKS WHERE THERE IS NO AWARENESS",
]

# ─────────────────────────────────────────────
# VALIDATION SYSTEM
# ─────────────────────────────────────────────

BANNED = [
    "HUSTLE", "GRIND", "DREAM", "BELIEVE",
    "SUCCESS", "GOALS", "MOTIVATION"
]

def _contains_banned(text):
    t = text.upper()
    return any(b in t for b in BANNED)


def _has_specificity(text):
    signals = [
        "MONEY", "SALARY", "ACCOUNT", "BALANCE",
        "SPEND", "SAVE", "MONTH", "RUPEE"
    ]
    return any(s in text for s in signals)


def _has_tension(text):
    tension_words = ["BUT", "STILL", "JUST"]
    return any(t in text for t in tension_words)


def _hook_strength(hook):
    words = hook.split()

    if len(words) < 3:
        return False

    weak = ["LIFE", "SUCCESS", "PEOPLE"]
    if words[0] in weak:
        return False

    return True


def _score(script_lines):
    text = " ".join(script_lines)

    score = 0

    if _has_specificity(text):
        score += 3

    if _has_tension(text):
        score += 3

    if not _contains_banned(text):
        score += 2

    if _hook_strength(script_lines[0]):
        score += 2

    return score


# ─────────────────────────────────────────────
# GENERATION LOGIC
# ─────────────────────────────────────────────

def _generate_once():
    hook = random.choice(HOOKS)
    scenario = random.choice(SCENARIOS)
    payoff = random.choice(PAYOFFS)

    return [hook, scenario, payoff]


def _generate_best(n=5):
    candidates = []

    for _ in range(n):
        script = _generate_once()
        score = _score(script)
        candidates.append((score, script))

    candidates.sort(reverse=True, key=lambda x: x[0])

    best_score, best_script = candidates[0]

    if best_score < 5:
        log.warning("Low quality script generated")

    return best_script


# ─────────────────────────────────────────────
# CLEANING (NO PUNCTUATION STRICT)
# ─────────────────────────────────────────────

def _clean(text):
    text = re.sub(r'[^A-Za-z0-9 ]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip().upper()


# ─────────────────────────────────────────────
# MAIN FUNCTION (PIPELINE COMPATIBLE)
# ─────────────────────────────────────────────

def generate_content():
    script = _generate_best()

    cleaned = []
    for line in script:
        clean_line = _clean(line)

        words = clean_line.split()
        if len(words) > 8:
            clean_line = " ".join(words[:8])

        cleaned.append({
            "text": clean_line,
            "highlight": clean_line.split()[-1]
        })

    content = " ".join(p["text"] for p in cleaned)

    return {
        "phrases": cleaned,
        "content": content,
        "hook": cleaned[0]["text"],
        "answer": cleaned[-1]["text"],
        "mood": "dark_truth",
        "title": cleaned[0]["text"] + " HITS HARD",
        "description": content
    }
