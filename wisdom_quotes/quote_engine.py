import json
import random
import os

QUOTES_FILE = "wisdom_quotes/quotes.json"
USED_FILE = "wisdom_quotes/used_quotes.json"


def _load_quotes():
    with open(QUOTES_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def _load_used():
    if os.path.exists(USED_FILE):
        with open(USED_FILE, 'r') as f:
            return json.load(f)
    return []


def _save_used(used):
    with open(USED_FILE, 'w') as f:
        json.dump(used, f, indent=2)


def get_next_quote():
    quotes = _load_quotes()
    used = _load_used()

    available = [i for i in range(len(quotes)) if i not in used]

    if not available:
        print("All quotes used — resetting.")
        used = []
        available = list(range(len(quotes)))

    idx = random.choice(available)
    used.append(idx)
    _save_used(used)

    print(f"Selected quote #{idx}: {quotes[idx][:60]}...")
    return quotes[idx]
