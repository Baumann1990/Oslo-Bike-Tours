# Oslo Bike Tours – Auto-Poster Setup Instructions

## What this system does

When you email tour photos to **turboflekkefjord@gmail.com**, the system
automatically detects the email, downloads the images, generates a marketing
caption using Claude AI, and posts the photo to the **Oslo Bike Tours Facebook
page** (and Instagram, once connected).

---

## Files in this folder

| File | Purpose |
|------|---------|
| `poster.py` | Main automation script — run this on your Mac |
| `config.json` | API credentials (Facebook page token etc.) |
| `processed_messages.json` | Tracks which emails have already been posted |
| `run_log.md` | Append-only log of every run |
| `images/` | Downloaded tour photos |
| `setup_mac_scheduler.sh` | Installs automatic scheduling on your Mac |

---

## Quick start — test it manually right now

```bash
cd ~/Documents/oslo-tours
python3 poster.py --test
```

This posts the most recent image in `images/` to Facebook immediately.

---

## Full automated setup (one-time)

### Step 1 – Install Python dependencies

```bash
pip3 install google-auth google-auth-oauthlib google-auth-httplib2 \
             google-api-python-client requests anthropic pillow
```

### Step 2 – Set your Anthropic API key

Add this to your `~/.zshrc` (or run it before each use):

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

Get your key from: https://console.anthropic.com/settings/api-keys

### Step 3 – Set up Gmail access (one-time OAuth)

1. Go to https://console.cloud.google.com
2. Create a project called "Oslo Tours Poster"
3. Enable the **Gmail API** (APIs & Services → Library → search Gmail API)
4. Go to **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**
5. Choose **Desktop app** as the application type
6. Download the JSON file and save it as:
   `~/Documents/oslo-tours/gmail_credentials.json`
7. Run `python3 poster.py` once — a browser window opens for Gmail authorization
8. After approving, a `gmail_token.json` is saved and future runs are automatic

### Step 4 – Install Mac scheduler (runs automatically at 9 AM & 5 PM)

```bash
chmod +x ~/Documents/oslo-tours/setup_mac_scheduler.sh
~/Documents/oslo-tours/setup_mac_scheduler.sh
```

That's it! The Mac will now run the poster automatically twice a day.

---

## Instagram setup (when ready)

The Facebook page currently has no Instagram Business account connected.
To enable Instagram posting:

1. Open the Oslo Bike Tours **Facebook Page**
2. Go to **Settings → Linked accounts → Instagram**
3. Connect your Instagram Business or Creator account
4. Then run this in Terminal to get the Instagram account ID:
   ```bash
   curl "https://graph.facebook.com/v25.0/1104222602768422?fields=instagram_business_account&access_token=PAGE_TOKEN_HERE"
   ```
5. Update `config.json` — set `instagram_account_id` to the returned ID

---

## Workflow: sending tour photos

Simply **email photos** to: **turboflekkefjord@gmail.com**

- Subject line doesn't matter
- Attach 1 or more JPEG/PNG images
- The system picks the largest image as the hero photo
- The Mac scheduler checks every morning and evening
- Posts are logged in `run_log.md`

---

## Token expiry

The `page_access_token` in `config.json` is **permanent** (never expires).
You do not need to refresh it unless you revoke app access.

If you ever get an auth error, regenerate with:
1. Go to https://developers.facebook.com/tools/explorer/
2. Select app "Oslo Bike Tours poster"
3. Add permissions: `pages_manage_posts`, `pages_read_engagement`, `instagram_content_publish`
4. Click **Generate Access Token**
5. Run in browser console:
   ```javascript
   fetch(`https://graph.facebook.com/v25.0/1104222602768422?fields=access_token&access_token=USER_TOKEN_HERE`)
     .then(r => r.json()).then(d => console.log(d.access_token))
   ```
6. Paste the new token into `config.json` → `page_access_token`

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `gmail_credentials.json not found` | Follow Step 3 above |
| `ANTHROPIC_API_KEY not set` | Posts without AI caption (uses default text) |
| Facebook error 190 (token invalid) | Regenerate page token (see above) |
| Instagram error 100 | Connect Instagram to Facebook page first |
| No emails found | Check `processed_messages.json` — the email may already be marked as processed |
