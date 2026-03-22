<div align="center">

```
██████╗ ██╗██╗     ██╗     ██╗ ██████╗ ███╗   ██╗ █████╗ ██╗██████╗ ███████╗
██╔══██╗██║██║     ██║     ██║██╔═══██╗████╗  ██║██╔══██╗██║██╔══██╗██╔════╝
██████╔╝██║██║     ██║     ██║██║   ██║██╔██╗ ██║███████║██║██████╔╝█████╗  
██╔══██╗██║██║     ██║     ██║██║   ██║██║╚██╗██║██╔══██║██║██╔══██╗██╔══╝  
██████╔╝██║███████╗███████╗██║╚██████╔╝██║ ╚████║██║  ██║██║██║  ██║███████╗
╚═════╝ ╚═╝╚══════╝╚══════╝╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝╚═╝  ╚═╝╚══════╝
```

### **_Thoughts** — Fully Autonomous YouTube Shorts Engine

*Generates. Renders. Uploads. Repeats. You do nothing.*

[![GitHub Actions](https://img.shields.io/badge/Powered%20By-GitHub%20Actions-2088FF?style=for-the-badge&logo=github-actions&logoColor=white)](https://github.com/features/actions)
[![Python](https://img.shields.io/badge/Python-3.11-FFD43B?style=for-the-badge&logo=python&logoColor=blue)](https://python.org)
[![Groq AI](https://img.shields.io/badge/AI-Groq%20LLaMA%203.1-F55036?style=for-the-badge&logo=meta&logoColor=white)](https://groq.com)
[![YouTube](https://img.shields.io/badge/YouTube-Shorts-FF0000?style=for-the-badge&logo=youtube&logoColor=white)](https://youtube.com)
[![License](https://img.shields.io/badge/License-MIT-00C853?style=for-the-badge)](LICENSE)

---

**3 uploads per day. 3 target audiences. 0 manual work.**

[🚀 Quick Start](#-quick-start-60-minutes) · [⚙️ How It Works](#️-how-it-works) · [🗂️ Architecture](#️-system-architecture) · [📋 Setup Guide](#-complete-setup-guide) · [🔑 Secrets Reference](#-github-secrets-reference)

</div>

---

## 🧠 What Is This?

This is a **fully autonomous content engine** for YouTube Shorts. Once deployed, it runs every single day without you touching anything — generating AI-written motivational content, rendering a cinematic 1080×1920 video, and uploading it to YouTube, Instagram, and Facebook at the exact moment your audience is most active.

Every Sunday, it analyses its own performance, identifies what worked, and generates new content ideas for the following week — automatically fed back into the pipeline.

**It is, in the truest sense, a self-improving content machine.**

```
You set it up once.
It runs forever.
It gets smarter every week.
```

---

## ⚡ What Happens Every Day

| Time | Audience | What Fires |
|---|---|---|
| 9:00 PM IST (weekdays) | 🌏 **Asia** | India, Pakistan, SEA, Middle East |
| 9:00 PM IST (weekends) | 🌏 **Asia** | 11:00 AM upload |
| 9:00 PM CET (weekdays) | 🌍 **Europe** | Stoic/philosophical content |
| 11:00 AM CET (weekends) | 🌍 **Europe** | Weekend morning slot |
| 8:00 PM EST (weekdays) | 🌎 **US** | Raw attitude content |
| 11:00 AM EST (weekends) | 🌎 **US** | Weekend morning slot |
| **Every Sunday 9:30 AM IST** | 📊 **Analytics** | Weekly report + new content ideas generated |

---

## ⚙️ How It Works

### The Daily Pipeline (runs 3× per day)

```
┌─────────────────────────────────────────────────────────────────────┐
│                     GITHUB ACTIONS TRIGGER                          │
│                  (cron schedule — zero human input)                 │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 1 — CONTENT GENERATION (quote_engine.py)                     │
│                                                                     │
│  • Groq LLaMA 3.1 generates a phrase-by-phrase motivational quote  │
│  • Picks from 6 viral structures: BUILD_UP, IF_THEN, REFRAME,      │
│    DARK_TRUTH, ANIMAL_POWER, NEVER_DO                              │
│  • Validates: no fake stats, no banned clichés, 3-5 phrases        │
│  • Retries up to 3× if output fails validation                     │
│  • Uses AI-generated ideas from last Sunday's analytics if fresh   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 2 — VIDEO CREATION (video_creator.py)                        │
│                                                                     │
│  • Searches Pexels for a cinematic background video matching mood  │
│  • Crops landscape → 9:16 vertical, scales to exact 1080×1920     │
│  • Darkens background 40% for text contrast                        │
│  • Renders each phrase as its own cut (2.5 seconds per phrase)     │
│  • Highlighted keyword shown in gold/cyan — one word per phrase    │
│  • Adds channel watermark + accent bar on every frame              │
│  • Appends a 3-second "Follow" outro                               │
│  • Mixes in royalty-free trap music at 30% volume with fade-out    │
│  • Final re-encode guarantees 1080×1920 @ 30fps                   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 3 — YOUTUBE UPLOAD (youtube_uploader.py)                     │
│                                                                     │
│  • OAuth2 token auto-refreshes — never expires                     │
│  • Resumable chunked upload (1MB chunks)                           │
│  • Auto-retries on 429/500/502/503/504 with exponential backoff    │
│  • Sets title, description, tags, hashtags, category               │
│  • Published as Public Short immediately                           │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 4 — INSTAGRAM UPLOAD (instagram_uploader.py)  [Optional]     │
│                                                                     │
│  • Uploads video to file.io to get a temporary public HTTPS URL    │
│  • Creates Instagram Reel container via Graph API                  │
│  • Polls processing status every 10s (up to 6 minutes)            │
│  • Publishes Reel — failure here does NOT stop YouTube upload      │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 5 — FACEBOOK UPLOAD (facebook_uploader.py)  [Optional]       │
│                                                                     │
│  • Chunked upload directly to Facebook Page via Graph API          │
│  • Published as a Facebook Reel                                    │
│  • Failure here does NOT stop YouTube upload                       │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  LOGGING + CLEANUP                                                  │
│                                                                     │
│  • Upload logged to .logs/uploads.json (last 500 entries)          │
│  • Failure logged to .logs/failures.json (last 200 entries)        │
│  • All temp video files deleted — zero storage accumulation        │
│  • Error email sent instantly if anything fails (notifier.py)      │
└─────────────────────────────────────────────────────────────────────┘
```

---

### The Weekly Intelligence Loop (every Sunday)

This is what makes the system **self-improving**. Every Sunday at 9:30 AM IST:

```
┌─────────────────────────────────────────────────────────────────────┐
│  analytics.py                                                       │
│                                                                     │
│  1. Pulls last 7 days of data from YouTube Analytics API           │
│     → Total views, watch time, likes, subscribers gained/lost      │
│     → Per-video performance for top 20 videos                      │
│     → Video titles enriched from YouTube Data API                  │
│                                                                     │
│  2. Feeds ALL data to Groq LLaMA 3.1 with this prompt:             │
│     "You are a YouTube growth analyst. Analyse this week's data.   │
│      Identify patterns, calculate conversion rates, generate        │
│      10 specific content ideas for next week."                      │
│                                                                     │
│  3. Groq returns structured JSON:                                   │
│     • patterns_that_worked                                          │
│     • patterns_that_failed                                          │
│     • sub_conversion_rate + benchmark                               │
│     • 3 immediate action items                                      │
│     • 10 next_week_ideas (specific angles, not generic)            │
│                                                                     │
│  4. Ideas saved → .logs/next_week_ideas.json                       │
│     → Git committed back to repo automatically                      │
│     → pipeline.py reads these next week instead of defaults        │
│                                                                     │
│  5. Full HTML report emailed to you with:                          │
│     → Stats dashboard (views, subs, watch time, uploads)           │
│     → Top 5 videos with visual bars                                │
│     → What worked / what failed                                    │
│     → 3 action items                                               │
│     → All 10 next week's ideas                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🗂️ System Architecture

```
billionaire-thoughts/
│
├── 📋 pipeline.py              ← Master orchestrator — runs everything
├── 🧠 quote_engine.py          ← Groq AI content generation + validation  
├── 🎬 video_creator.py         ← FFmpeg video rendering engine
├── 📤 youtube_uploader.py      ← YouTube OAuth2 upload with retry
├── 📱 instagram_uploader.py    ← Instagram Reels via Graph API
├── 👥 facebook_uploader.py     ← Facebook Page Reels via Graph API
├── 📊 analytics.py             ← Weekly YouTube analytics + AI analysis
├── 📧 notifier.py              ← Email alerts + weekly HTML reports
├── ⚙️  config.py               ← All settings, audience profiles, themes
│
├── 🔧 setup_auth.py            ← One-time YouTube OAuth setup
├── 🎵 setup_music.py           ← Downloads 5 royalty-free tracks
├── 🔤 setup_fonts.py           ← Downloads Montserrat font
│
├── 🎵 music/                   ← Royalty-free trap beats (committed to repo)
├── 🔤 fonts/                   ← Montserrat Bold/Regular (committed to repo)
├── 📁 .logs/                   ← uploads.json, failures.json, next_week_ideas.json
├── 📁 .temp/                   ← Video rendering workspace (auto-cleaned)
│
└── 🤖 .github/workflows/
    ├── upload_asia.yml         ← Triggers daily for Asia audience
    ├── upload_europe.yml       ← Triggers daily for Europe audience
    ├── upload_us.yml           ← Triggers daily for US audience
    └── weekly_report.yml       ← Triggers every Sunday for analytics
```

---

## 🎯 Audience Targeting System

The pipeline runs three parallel tracks — each with its own tone, themes, tags, and upload schedule:

| Audience | Age Group | Tone | Example Theme |
|---|---|---|---|
| 🌎 **US** | 16–35 males globally | Raw, direct, attitude-driven | *"The wolf doesn't explain itself to sheep"* |
| 🌍 **Europe** | 18–34 European males | Stoic, philosophical, devastating | *"Society fears the man who thinks for himself"* |
| 🌏 **Asia** | 16–30 India/Pakistan/SEA/ME | Poetic, struggle-based, validating | *"The man who came from nothing has a fire that cannot be extinguished"* |

Each audience gets its own: content themes, YouTube tags, hashtags, upload timing, and description CTA.

---

## 🎬 Video Structure

Every Short follows a **phrase-by-phrase cut structure** engineered for maximum retention:

```
┌─────────────────────────────────┐
│                                 │  ← Cinematic Pexels background
│   [PHRASE 1]    2.5s           │     (wolf, lion, eagle, dark city...)
│   "THE STRONGEST MEN"          │
│         ^^^^^^^^^^^            │  ← Gold/cyan keyword highlight
│   yt | Channel Name ──────────│  ← Watermark
│ ▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬ │  ← Accent bar
└─────────────────────────────────┘
           ↓ CUT ↓
┌─────────────────────────────────┐
│   [PHRASE 2]    2.5s           │
│   "NEVER ANNOUNCE"             │
└─────────────────────────────────┘
           ↓ CUT ↓
┌─────────────────────────────────┐
│   [PHRASE 3]    2.5s           │
│   "THEIR NEXT MOVE"            │
└─────────────────────────────────┘
           ↓ CUT ↓
┌─────────────────────────────────┐
│   Follow for more      3s      │  ← Outro frame
│        💰                       │
│   Channel Name                 │
│   New video every night        │
└─────────────────────────────────┘

Total: ~13 seconds | 1080×1920 | 30fps | Trap music at 30% volume
```

**6 Viral Structures in rotation:**

| Structure | Description |
|---|---|
| `BUILD_UP` | 4 phrases building tension — each adds one more layer |
| `IF_THEN` | IF condition → action → consequence → karma |
| `REFRAME` | Takes a painful word, reframes it as hidden strength |
| `DARK_TRUTH` | Escalating dark observations about how life really works |
| `ANIMAL_POWER` | Animal analogy for silent strength and attitude |
| `NEVER_DO` | Things a real man never does — 4 complete thoughts |

---

## 🛡️ Reliability Features

The pipeline is built to **never silently fail**:

- **Retry logic** — Groq API calls retry 4× with exponential backoff
- **YouTube retry** — Auto-retries on 429/500/502/503/504 errors
- **Instagram/Facebook isolation** — Social failures never kill the YouTube upload
- **Content validation** — Rejects fake statistics, banned clichés before upload
- **Resolution guarantee** — FFmpeg scale filter enforces 1080×1920 at every stage
- **Instant error emails** — Failure sends an HTML email with exact fix steps
- **Token auto-refresh** — YouTube OAuth never expires mid-pipeline
- **Gradient fallback** — If Pexels fails, renders a cinematic gradient background

---

## 🚀 Quick Start (60 minutes)

### Prerequisites

- [ ] Windows PC with Python 3.10+
- [ ] Git installed
- [ ] GitHub account
- [ ] Groq API key → [console.groq.com/keys](https://console.groq.com/keys)
- [ ] Gmail account (for alerts)

### 1. Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/billionaire-thoughts.git
cd billionaire-thoughts
pip install -r requirements.txt
```

### 2. Get YouTube Token (most important step)

```bash
# First: download client_secret.json from Google Cloud Console
# (Full instructions in SETUP_GUIDE.md → Step 3)

python setup_auth.py
# Browser opens → login → copy the two base64 blocks printed in terminal
```

Add both blocks as GitHub Secrets: `YOUTUBE_TOKEN_JSON` and `YOUTUBE_CLIENT_SECRET_JSON`

### 3. Download Assets

```bash
python setup_music.py   # Downloads 5 royalty-free trap beats
python setup_fonts.py   # Downloads Montserrat font

git add music/ fonts/
git commit -m "Add assets"
git push
```

### 4. Add All GitHub Secrets

`Settings → Secrets and variables → Actions → New repository secret`

See the full table below.

### 5. Test Run

`Actions tab → Upload — US → Run workflow → watch logs`

If green: you're done. It runs automatically forever.

---

## 🔑 GitHub Secrets Reference

| Secret Name | Required | Where to Get It |
|---|---|---|
| `GROQ_API_KEY` | ✅ Yes | [console.groq.com/keys](https://console.groq.com/keys) |
| `YOUTUBE_TOKEN_JSON` | ✅ Yes | Output of `python setup_auth.py` |
| `YOUTUBE_CLIENT_SECRET_JSON` | ✅ Yes | Output of `python setup_auth.py` |
| `ALERT_EMAIL` | ✅ Yes | Your Gmail address |
| `EMAIL_SENDER` | ✅ Yes | Your Gmail address (same) |
| `EMAIL_APP_PASSWORD` | ✅ Yes | Gmail → Security → App Passwords |
| `CHANNEL_NAME` | ✅ Yes | Your YouTube channel name |
| `PEXELS_API_KEY` | ✅ Yes | [pexels.com/api](https://www.pexels.com/api/) — free |
| `INSTAGRAM_ACCESS_TOKEN` | ⚪ Optional | [developers.facebook.com](https://developers.facebook.com) |
| `INSTAGRAM_USER_ID` | ⚪ Optional | Facebook API Explorer |
| `FACEBOOK_ACCESS_TOKEN` | ⚪ Optional | [developers.facebook.com](https://developers.facebook.com) |
| `FACEBOOK_PAGE_ID` | ⚪ Optional | Your Facebook Page settings |

---

## 📊 Weekly Report Preview

Every Sunday you receive an HTML email containing:

```
┌─────────────────────────────────────────┐
│  BillionAire's _Thoughts 💰             │
│  Weekly Intelligence Report             │
├──────────┬──────────┬──────────┬────────┤
│  12,847  │   +234   │  214 hrs │   21   │
│  Views   │   Subs   │  Watch   │Uploads │
├─────────────────────────────────────────┤
│  AI Summary (Groq analysis)             │
│  Subscribe conversion rate: 1.82% ✅    │
├─────────────────────────────────────────┤
│  TOP VIDEOS THIS WEEK                   │
│  1. "The wolf doesn't explain..." ████  │
│  2. "If you hurt someone..."      ███   │
│  3. "Every downfall is..."        ██    │
├─────────────────────────────────────────┤
│  ✅ WHAT WORKED                         │
│  ❌ WHAT FAILED                         │
│  ⚡ 3 ACTIONS FOR THIS WEEK            │
│  💡 10 IDEAS AUTO-LOADED TO PIPELINE   │
└─────────────────────────────────────────┘
```

The 10 ideas at the bottom are **automatically committed to the repo** and used by next week's pipeline instead of the default themes. No action needed from you.

---

## 🔧 Customisation

All settings live in `config.py` (loaded from environment variables):

```python
# Change video timing
SECONDS_PER_PHRASE = 2.5    # How long each phrase stays on screen
OUTRO_DURATION_SECONDS = 3  # Follow CTA duration
MAX_PHRASES = 5             # Max phrases per quote

# Change video quality
VIDEO_WIDTH  = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS    = 30

# Change upload privacy for testing
YOUTUBE_PRIVACY = "unlisted"  # "public" for live
```

To add or edit content themes, edit the `AUDIENCE_PROFILES` dictionary in `config.py` for the relevant audience (`us`, `europe`, `asia`).

---

## 🩺 Troubleshooting

| Error | Fix |
|---|---|
| `GROQ_API_KEY not set` | Add `GROQ_API_KEY` to GitHub Secrets |
| `youtube_token.json not found` | Re-run `python setup_auth.py` and update secrets |
| `FFmpeg not found` | Ensure workflow yml has `sudo apt-get install -y ffmpeg` |
| `No music files found` | Run `python setup_music.py` then commit `music/` folder |
| `Quota exceeded` (YouTube) | You hit 6 uploads/day limit — wait for midnight UTC reset |
| Instagram/Facebook token expired | Tokens last 60 days — check error email for exact fix steps |
| `RESOLUTION MISMATCH` in logs | Delete `.temp/` folder and re-run |

---

## 📁 Log Files

The pipeline maintains three JSON logs in `.logs/`:

| File | Contents |
|---|---|
| `uploads.json` | Last 500 successful uploads with video ID, title, mood, platforms |
| `failures.json` | Last 200 failures with step name, audience, error message |
| `next_week_ideas.json` | 10 Groq-generated content ideas, refreshed every Sunday |

These are gitignored by default. `next_week_ideas.json` is the exception — it gets committed by the weekly workflow so the pipeline can access it on the next run.

---

## 📦 Tech Stack

| Layer | Technology |
|---|---|
| **Runtime** | Python 3.11 |
| **CI/CD** | GitHub Actions (free tier) |
| **AI Content** | Groq API — LLaMA 3.1 8B Instant |
| **Video Rendering** | FFmpeg + Pillow (PIL) |
| **Stock Footage** | Pexels API (free) |
| **YouTube API** | Google Data API v3 + Analytics API v2 |
| **Social APIs** | Instagram Graph API + Facebook Graph API v18 |
| **Email** | Gmail SMTP + App Password |
| **HTTP** | httpx + requests + tenacity (retry) |
| **Auth** | Google OAuth2 with auto-refresh |

---

## 📄 License

MIT License — use it, fork it, build on it.

---

<div align="center">

**Built to run forever. Designed to grow smarter every week.**

*Set it up once. Walk away. Come back to a growing channel.*

</div>
