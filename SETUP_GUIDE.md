# SETUP GUIDE — BillionAire's_Thoughts 😎
**Complete setup from zero to automated uploads — estimated time: 60–90 minutes**

After setup, this pipeline will:
- Run 3× every day at 6 PM, 7 PM, 8 PM IST
- Generate a finance video with AI content
- Upload to YouTube automatically
- Email you if anything breaks, with exact fix steps
- Send a weekly summary to your email every Sunday

You do **nothing** after setup.

---

## What You Need Before Starting

- [ ] Windows PC with Python 3.10+ installed
- [ ] Git installed (https://git-scm.com/download/win)
- [ ] GitHub account (you already have this)
- [ ] Groq API key (you already have this)
- [ ] Gmail account (mohanreddythippireddy14@gmail.com)

---

## Step 1 — Create the GitHub Repository

1. Go to https://github.com/new
2. Repository name: `billionaire-thoughts`
3. Set to **Private** (your API keys will be here as Secrets — never public)
4. Click **Create repository**
5. On your PC, open a terminal (Win + R → type `cmd` → Enter):
```
cd Desktop
git clone https://github.com/YOUR_USERNAME/billionaire-thoughts.git
cd billionaire-thoughts
```
6. Copy all the project files into this folder
7. Commit everything:
```
git add .
git commit -m "Initial setup"
git push
```

---

## Step 2 — Install Python Dependencies

In the same terminal:
```
pip install -r requirements.txt
```

Wait for it to finish. If you see errors, run:
```
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## Step 3 — Get Your YouTube Token (one-time, takes 5 minutes)

This is the most important step. Do it carefully.

**First, create a Google Cloud project:**

1. Go to https://console.cloud.google.com/
2. Click "Select a project" at the top → "New Project"
3. Name: `BillionaireThoughts` → Create
4. Left menu → "APIs & Services" → "Library"
5. Search `YouTube Data API v3` → click it → **Enable**
6. Left menu → "APIs & Services" → "Credentials"
7. Click "+ Create Credentials" → "OAuth client ID"
8. If asked to configure consent screen:
   - User type: **External** → Create
   - App name: `BillionaireThoughts`
   - User support email: your Gmail
   - Developer contact email: your Gmail
   - Save and Continue through all screens
   - Back on Credentials page: click "+ Create Credentials" → "OAuth client ID" again
9. Application type: **Desktop app**
10. Name: `BillionaireThoughts` → Create
11. Click the **download button (↓)** on the newly created credential
12. Save the file as `client_secret.json` in your project folder

**Now run the auth script:**
```
python setup_auth.py
```

A browser will open. Log in with the Google account that owns your YouTube channel.  
After login, your terminal will show two long blocks of text.

**Copy the first block (YOUTUBE_TOKEN_JSON) and add it as a GitHub Secret:**
1. Go to your GitHub repo → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Name: `YOUTUBE_TOKEN_JSON`
4. Value: paste the first long text block
5. Add secret

**Copy the second block (YOUTUBE_CLIENT_SECRET_JSON) and add it:**
1. New repository secret
2. Name: `YOUTUBE_CLIENT_SECRET_JSON`
3. Value: paste the second long text block
4. Add secret

---

## Step 4 — Add Groq API Key

1. Go to https://console.groq.com/keys
2. Copy your key
3. GitHub repo → Settings → Secrets → New secret
4. Name: `GROQ_API_KEY`
5. Value: your key
6. Add secret

---

## Step 5 — Set Up Email Alerts

You'll get error emails and weekly reports sent to mohanreddythippireddy14@gmail.com.

**Create a Gmail App Password:**
1. Go to https://myaccount.google.com/security
2. Make sure **2-Step Verification** is ON (if not, enable it first)
3. Search for "App passwords" in the Google Account search bar
4. Create app → select "Mail" → select "Windows Computer"
5. Click Generate → copy the 16-character password

**Add to GitHub Secrets:**
- Name: `EMAIL_SENDER` → Value: `mohanreddythippireddy14@gmail.com`
- Name: `EMAIL_APP_PASSWORD` → Value: the 16-character password from above

---

## Step 6 — Download Music (run once, commit once)

In your terminal:
```
python setup_music.py
```

This downloads 5 free royalty-free trap beats.

Then commit them to GitHub:
```
git add music/
git commit -m "Add music tracks"
git push
```

---

## Step 7 — Download Font (optional but recommended)

```
python setup_fonts.py
git add fonts/
git commit -m "Add Montserrat font"
git push
```

If this fails, the pipeline still works with a fallback font.

---

## Step 8 — Test It Manually Before Going Live

Go to your GitHub repo → **Actions** tab → **Upload Video** → **Run workflow** → Run workflow

Watch the logs. It should take 5–8 minutes.

**If it succeeds:** 🎉 You're done. The pipeline will now run automatically every day.

**If it fails:** Check the red error message in the logs and look it up in the Troubleshooting section below. You'll also get an email at mohanreddythippireddy14@gmail.com with fix steps.

---

## Step 9 — Set Up Instagram (Optional)

If you want videos also posted to Instagram:

1. Convert your Instagram to a **Professional account** (Creator or Business)
   - Profile → Settings → Account → Switch to Professional account
2. Connect it to a **Facebook Page** (create one if you don't have one)
3. Go to https://developers.facebook.com/
4. Create a new app → Business → add Instagram Graph API
5. Get a long-lived User Access Token with permission: `instagram_content_publish`
6. Find your Instagram User ID (visible in the API Explorer)
7. Add to GitHub Secrets:
   - `INSTAGRAM_ACCESS_TOKEN` → your access token
   - `INSTAGRAM_USER_ID` → your Instagram user ID

**Note:** Instagram tokens expire after 60 days. You'll get an email alert when they break.

---

## Step 10 — Set Up Facebook (Optional)

1. Create a Facebook Page for your channel if you don't have one
2. Go to https://developers.facebook.com/tools/explorer
3. Get a Page Access Token with permission: `pages_manage_posts`
4. Exchange it for a long-lived token (instructions in Meta docs)
5. Add to GitHub Secrets:
   - `FACEBOOK_ACCESS_TOKEN` → your page access token
   - `FACEBOOK_PAGE_ID` → your Facebook Page ID (visible in Page settings)

---

## Summary: All GitHub Secrets Needed

| Secret Name | Required? | Where to get it |
|---|---|---|
| `GROQ_API_KEY` | ✅ Yes | console.groq.com/keys |
| `YOUTUBE_TOKEN_JSON` | ✅ Yes | Run `python setup_auth.py` |
| `YOUTUBE_CLIENT_SECRET_JSON` | ✅ Yes | Run `python setup_auth.py` |
| `EMAIL_SENDER` | ✅ Yes | Your Gmail address |
| `EMAIL_APP_PASSWORD` | ✅ Yes | Gmail → 2FA → App Passwords |
| `INSTAGRAM_ACCESS_TOKEN` | ⬜ Optional | developers.facebook.com |
| `INSTAGRAM_USER_ID` | ⬜ Optional | developers.facebook.com |
| `FACEBOOK_ACCESS_TOKEN` | ⬜ Optional | developers.facebook.com |
| `FACEBOOK_PAGE_ID` | ⬜ Optional | Your Facebook Page settings |

---

## Troubleshooting

**"GROQ_API_KEY is not set"**
→ Add GROQ_API_KEY to GitHub Secrets (Step 4)

**"youtube_token.json not found"**
→ Re-run `python setup_auth.py` and re-add the secrets (Step 3)

**"FFmpeg not found"**
→ Check that `.github/workflows/upload.yml` contains the line:  
`- run: sudo apt-get update -q && sudo apt-get install -y ffmpeg`

**"No music files found"**
→ Run `python setup_music.py` then `git add music/ && git commit -m "Music" && git push`

**Pipeline runs but nothing uploads**
→ Go to Actions tab → click the run → look for error messages in red

**"Quota exceeded" on YouTube**
→ This means you've uploaded 6 videos today (YouTube's daily limit for unverified apps).  
→ Wait until midnight UTC for the quota to reset.  
→ For higher limits: apply for quota increase at Google Cloud Console.

---

## How to Change Content Settings

Edit `config.py` to change:
- `CONTENT_THEMES` — what the AI generates content about
- `YOUTUBE_TAGS` — YouTube tags on every video
- `MAIN_DURATION_SECONDS` — how long the content section is
- `YOUTUBE_PRIVACY` — change to `"unlisted"` to test without going public

---

## Monthly Checklist (5 minutes)

- [ ] Check GitHub Actions → make sure there are no repeated failures
- [ ] Open YouTube Studio → check which videos performed best
- [ ] Check inbox for the Sunday weekly report email
- [ ] Renew Instagram/Facebook tokens if they expired (every 60 days)

---

*BillionAire's_Thoughts 😎 — automated, consistent, zero involvement.*
