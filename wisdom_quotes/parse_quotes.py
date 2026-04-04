"""
Run this ONCE locally after downloading the plain text version of
"A New Dictionary of Thoughts" from Archive.org.

Steps:
1. Go to https://archive.org/details/newdictionaryoft1927edwa
2. Download the plain text (.txt) version
3. Place it in this folder as 'book.txt'
4. Run: python parse_quotes.py
5. Commit the generated quotes.json to the repo
"""

import json
import re

INPUT_FILE = "wisdom_quotes/book.txt"
OUTPUT_FILE = "wisdom_quotes/quotes.json"

MIN_LENGTH = 40   # skip very short fragments
MAX_LENGTH = 280  # keep it short enough for a Short

def parse_quotes(text):
    # Split on common quote delimiters in the book
    # The book uses em-dashes and newlines to separate entries
    lines = text.split('\n')
    quotes = []

    for line in lines:
        line = line.strip()

        # Skip empty, headers, page numbers
        if not line or line.isdigit() or len(line) < MIN_LENGTH:
            continue
        if line.isupper():  # section headers like "AMBITION", "COURAGE"
            continue

        # Remove author attributions (lines ending with — Name or — Name, Source)
        cleaned = re.sub(r'—[^—]+$', '', line).strip()
        cleaned = re.sub(r'\s+', ' ', cleaned)

        if MIN_LENGTH <= len(cleaned) <= MAX_LENGTH:
            quotes.append(cleaned)

    # Deduplicate
    quotes = list(dict.fromkeys(quotes))
    return quotes


if __name__ == "__main__":
    with open(INPUT_FILE, 'r', encoding='utf-8', errors='ignore') as f:
        text = f.read()

    quotes = parse_quotes(text)

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(quotes, f, indent=2, ensure_ascii=False)

    print(f"Parsed {len(quotes)} quotes → {OUTPUT_FILE}")
