# setup_auth.py
# ============================================================
# ONE-TIME SETUP — Run this ONCE on your Windows PC
# You will NEVER need to run this again unless Google revokes your access
#
# What it does:
#   1. Opens your browser
#   2. You log in with your YouTube channel's Google account
#   3. Saves youtube_token.json with a refresh_token that lasts forever
#   4. Prints the base64-encoded token → you paste it into GitHub Secrets
#
# Run:  python setup_auth.py
# ============================================================

import base64
import json
import sys
from pathlib import Path

print("=" * 60)
print("  YouTube OAuth Setup")
print("  BillionAire's_Thoughts 😎")
print("=" * 60)

# ── Check client_secret.json ──────────────────────────────────
CLIENT_SECRET = Path("client_secret.json")
if not CLIENT_SECRET.exists():
    print("""
❌  client_secret.json not found!

You need to create this file from Google Cloud Console.
Here's exactly how:

  1. Go to: https://console.cloud.google.com/
  2. Click "Select a project" → "New Project" → name it anything
  3. In the left menu: APIs & Services → Library
  4. Search "YouTube Data API v3" → click it → Enable
  5. Left menu: APIs & Services → Credentials
  6. Click "+ Create Credentials" → OAuth client ID
  7. Application type: Desktop app → name it anything → Create
  8. Click the download button (↓) → save as client_secret.json
  9. Put client_secret.json in the same folder as this script
 10. Re-run: python setup_auth.py
""")
    sys.exit(1)

print("\n✓ client_secret.json found")

# ── Run OAuth flow ────────────────────────────────────────────
print("\nOpening browser for login...")
print("→ Log in with the Google account that owns your YouTube channel\n")

try:
    from google_auth_oauthlib.flow import InstalledAppFlow

    SCOPES = [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube.readonly",
        "https://www.googleapis.com/auth/yt-analytics.readonly",
    ]

    flow  = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
    creds = flow.run_local_server(port=8080, open_browser=True)

except Exception as exc:
    print(f"\n❌ Auth failed: {exc}")
    print("\nMake sure requirements are installed:")
    print("  pip install -r requirements.txt")
    sys.exit(1)

# ── Save token ────────────────────────────────────────────────
token_data = {
    "token":         creds.token,
    "refresh_token": creds.refresh_token,
    "token_uri":     creds.token_uri,
    "client_id":     creds.client_id,
    "client_secret": creds.client_secret,
    "scopes":        list(creds.scopes),
}
TOKEN_FILE = Path("youtube_token.json")
TOKEN_FILE.write_text(json.dumps(token_data, indent=2), encoding="utf-8")

print("\n✅ youtube_token.json created successfully!")

# ── Also save client_secret base64 ───────────────────────────
token_b64  = base64.b64encode(TOKEN_FILE.read_bytes()).decode()
secret_b64 = base64.b64encode(CLIENT_SECRET.read_bytes()).decode()

print("""
═══════════════════════════════════════════════════════════
  NEXT STEP: Add these to GitHub Secrets
  (Settings → Secrets and variables → Actions → New secret)
═══════════════════════════════════════════════════════════

SECRET 1 — Name: YOUTUBE_TOKEN_JSON
Value (copy EVERYTHING between the lines):
──────────────────────────────────────────""")
print(token_b64)
print("""──────────────────────────────────────────

SECRET 2 — Name: YOUTUBE_CLIENT_SECRET_JSON
Value (copy EVERYTHING between the lines):
──────────────────────────────────────────""")
print(secret_b64)
print("""──────────────────────────────────────────

After adding both secrets:
  ✓ Your pipeline will upload to YouTube automatically
  ✓ The token auto-refreshes — you never need to do this again

See SETUP_GUIDE.md for the remaining secrets to add.
""")
