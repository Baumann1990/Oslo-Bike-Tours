#!/usr/bin/env python3
"""
Oslo Bike Tours - Social Media Marketing Agent
Monitors Gmail for photos/videos → generates captions → posts to Facebook & Instagram
"""

import os
import json
import base64
import time
import re
import tempfile
import mimetypes
from pathlib import Path
from datetime import datetime, timezone
import requests

# PIL for image cropping (install: pip install Pillow --break-system-packages)
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# ── Config ────────────────────────────────────────────────────────────────────

CONFIG_PATH = Path(__file__).parent / "config.json"

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

# ── State (track already-processed message IDs) ───────────────────────────────

STATE_PATH = Path(__file__).parent / "processed_messages.json"

def load_state():
    if STATE_PATH.exists():
        with open(STATE_PATH) as f:
            return json.load(f)
    return {"processed": []}

def save_state(state):
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)

# ── Gmail (via Google API, using OAuth token from environment) ─────────────────
# We use the Gmail REST API with an OAuth token. Since we have Gmail MCP available,
# we'll use the gmail_search_messages approach via subprocess/MCP.
# For the scheduled runner, we call the MCP tools via the Claude API.
# This script uses the Gmail API directly via HTTP if GMAIL_ACCESS_TOKEN is set,
# otherwise it falls back to printing instructions.

def get_gmail_token():
    """Get Gmail OAuth token from environment."""
    return os.environ.get("GMAIL_ACCESS_TOKEN", "")

def search_gmail_messages(query, max_results=20):
    """Search Gmail messages using REST API."""
    token = get_gmail_token()
    if not token:
        return []
    url = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
    params = {"q": query, "maxResults": max_results}
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(url, params=params, headers=headers)
    if r.status_code != 200:
        print(f"Gmail search error: {r.status_code} {r.text}")
        return []
    data = r.json()
    return data.get("messages", [])

def get_gmail_message(message_id):
    """Get full Gmail message."""
    token = get_gmail_token()
    if not token:
        return None
    url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}"
    params = {"format": "full"}
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(url, params=params, headers=headers)
    if r.status_code != 200:
        return None
    return r.json()

def extract_attachments(message):
    """Extract image/video attachments from a Gmail message."""
    attachments = []
    token = get_gmail_token()

    def process_parts(parts):
        for part in parts:
            if part.get("parts"):
                process_parts(part["parts"])
            mime = part.get("mimeType", "")
            filename = part.get("filename", "")
            body = part.get("body", {})

            if mime.startswith("image/") or mime.startswith("video/"):
                attachment_id = body.get("attachmentId")
                data = body.get("data")

                if attachment_id and token:
                    # Fetch attachment data
                    msg_id = message["id"]
                    url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}/attachments/{attachment_id}"
                    r = requests.get(url, headers={"Authorization": f"Bearer {token}"})
                    if r.status_code == 200:
                        data = r.json().get("data", "")

                if data:
                    # Gmail uses URL-safe base64
                    raw = base64.urlsafe_b64decode(data + "==")
                    ext = mimetypes.guess_extension(mime) or ""
                    if not ext:
                        if mime == "image/jpeg":
                            ext = ".jpg"
                        elif mime == "image/png":
                            ext = ".png"
                        elif mime == "video/mp4":
                            ext = ".mp4"
                    attachments.append({
                        "filename": filename or f"attachment{ext}",
                        "mime_type": mime,
                        "data": raw,
                        "ext": ext,
                    })

    payload = message.get("payload", {})
    parts = payload.get("parts", [])
    if parts:
        process_parts(parts)

    return attachments

def get_email_subject(message):
    """Extract subject from Gmail message headers."""
    headers = message.get("payload", {}).get("headers", [])
    for h in headers:
        if h.get("name", "").lower() == "subject":
            return h.get("value", "")
    return ""

def get_email_body_text(message):
    """Extract plain text body from Gmail message."""
    def extract_text(parts):
        for part in parts:
            if part.get("parts"):
                result = extract_text(part["parts"])
                if result:
                    return result
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data", "")
                if data:
                    return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
        return ""

    payload = message.get("payload", {})
    if payload.get("mimeType") == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
    return extract_text(payload.get("parts", []))

# ── Caption generation via Claude API ─────────────────────────────────────────

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

CAPTION_SYSTEM_PROMPT = """You are writing social media captions for Oslo Bike Tours (oslobiketours.no), a guided bike tour company in Oslo, Norway.

Write like a normal person, not a travel blogger. Short, grounded, specific. No flowery language, no "wanderlust", no dramatic descriptions of light or seasons. Just honest, casual observations about cycling in Oslo — the kind of thing you'd actually say to a friend.

Rules:
- Keep it simple and direct. One or two sentences is often enough.
- No salesy language, no CTAs, no website links in the caption
- Avoid words like: stunning, incredible, unforgettable, magical, breathtaking, wanderlust, hidden gems
- Emojis: one or two at most, only if they feel natural
- Use context from the email if it tells you something specific about the photo or location
- For Instagram: add 6–8 relevant hashtags on a new line at the end
- For Facebook: 1–3 casual sentences, no hashtags

Respond with a JSON object:
{
  "instagram": "caption text\n\n#hashtag1 #hashtag2 ...",
  "facebook": "caption text"
}
"""

def generate_captions(subject, email_body, attachment_filenames):
    """Generate captions using Claude API."""
    if not ANTHROPIC_API_KEY:
        # Fallback captions
        return {
            "instagram": "Good day on the bikes in Oslo 🚲\n\n#OsloBikeTours #Oslo #CyclingOslo #VisitOslo #NorwayTravel #BikeLife #OsloCity #ExploreOslo",
            "facebook": "Good day out on the bikes. Oslo is a great city to explore this way."
        }

    user_msg = f"Email subject: {subject}\n\nEmail body: {email_body or '(no text)'}\n\nAttachments: {', '.join(attachment_filenames)}\n\nPlease write captions for these social media posts."

    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 600,
            "system": CAPTION_SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user_msg}],
        },
        timeout=30,
    )

    if response.status_code != 200:
        print(f"Claude API error: {response.status_code}")
        return None

    text = response.json()["content"][0]["text"]

    # Parse JSON from response
    try:
        # Find JSON object in response
        match = re.search(r'\{[^{}]*"instagram"[^{}]*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return json.loads(text)
    except Exception as e:
        print(f"Caption parse error: {e}\nRaw: {text}")
        return None

# ── Meta Graph API posting ─────────────────────────────────────────────────────

GRAPH_BASE = "https://graph.facebook.com/v19.0"

def get_page_access_token(system_user_token, page_id):
    """Exchange a system user token for a Page access token."""
    url = f"{GRAPH_BASE}/me/accounts"
    r = requests.get(url, params={"access_token": system_user_token})
    if r.status_code != 200:
        print(f"Failed to get page accounts: {r.status_code} {r.text}")
        return None
    data = r.json()
    for page in data.get("data", []):
        if page.get("id") == page_id:
            return page.get("access_token")
    print(f"Page {page_id} not found in accounts list.")
    return None

def post_to_facebook(page_id, access_token, caption, image_path=None, video_path=None):
    """Post to Facebook Page with optional media."""
    if image_path:
        url = f"{GRAPH_BASE}/{page_id}/photos"
        with open(image_path, "rb") as f:
            r = requests.post(url, data={
                "caption": caption,
                "access_token": access_token,
            }, files={"source": f})
    elif video_path:
        url = f"{GRAPH_BASE}/{page_id}/videos"
        with open(video_path, "rb") as f:
            r = requests.post(url, data={
                "description": caption,
                "access_token": access_token,
            }, files={"source": f})
    else:
        url = f"{GRAPH_BASE}/{page_id}/feed"
        r = requests.post(url, data={
            "message": caption,
            "access_token": access_token,
        })

    result = r.json()
    if "error" in result:
        print(f"Facebook post error: {result['error']}")
        return None
    print(f"✅ Facebook posted: {result}")
    return result

def upload_instagram_image(ig_account_id, access_token, image_path, caption):
    """Upload image to Instagram (step 1: create container)."""
    # For Instagram, we need a publicly accessible URL.
    # We'll upload to Facebook first and use the URL, or use imgbb/imgur.
    # Alternative: use the page's photo and cross-post.
    # Simplest approach: upload photo to FB page then use IG container with image_url.
    pass

def post_image_to_instagram(ig_account_id, access_token, image_url, caption):
    """Post image to Instagram using a public URL."""
    # Step 1: Create media container
    url = f"{GRAPH_BASE}/{ig_account_id}/media"
    r = requests.post(url, data={
        "image_url": image_url,
        "caption": caption,
        "access_token": access_token,
    })
    result = r.json()
    if "error" in result:
        print(f"Instagram container error: {result['error']}")
        return None

    container_id = result.get("id")
    if not container_id:
        return None

    # Step 2: Wait for container to be ready, then publish
    status_url = f"{GRAPH_BASE}/{container_id}"
    for attempt in range(6):
        time.sleep(5)
        status_r = requests.get(status_url, params={
            "fields": "status_code",
            "access_token": access_token,
        })
        status = status_r.json().get("status_code", "")
        if status == "FINISHED":
            break
        if status == "ERROR":
            print(f"   ⚠️  Instagram container processing failed.")
            return None
        print(f"   ⏳ Container status: {status} (attempt {attempt+1}/6)")

    pub_url = f"{GRAPH_BASE}/{ig_account_id}/media_publish"
    r2 = requests.post(pub_url, data={
        "creation_id": container_id,
        "access_token": access_token,
    })
    result2 = r2.json()
    if "error" in result2:
        print(f"Instagram publish error: {result2['error']}")
        return None

    print(f"✅ Instagram posted: {result2}")
    return result2

def crop_for_instagram(image_path):
    """Crop image to 4:5 portrait ratio (Instagram's preferred format).
    Returns path to cropped temp file, or original path if PIL not available."""
    if not HAS_PIL:
        print("   ⚠️  Pillow not installed — posting uncropped (may fail on Instagram).")
        return image_path

    img = Image.open(image_path)
    w, h = img.size

    # Instagram accepts ratios between 4:5 (portrait) and 1.91:1 (landscape).
    # We target 4:5 (0.8 width/height) — best for engagement on mobile.
    target_ratio = 4 / 5  # width / height

    current_ratio = w / h
    if abs(current_ratio - target_ratio) < 0.02:
        return image_path  # Already close enough

    if current_ratio > target_ratio:
        # Too wide — crop the sides
        new_w = int(h * target_ratio)
        left = (w - new_w) // 2
        img = img.crop((left, 0, left + new_w, h))
    else:
        # Too tall — crop top/bottom (keep center)
        new_h = int(w / target_ratio)
        top = (h - new_h) // 2
        img = img.crop((0, top, w, top + new_h))

    # Save to a new temp file
    suffix = Path(image_path).suffix or ".jpg"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        img.save(tmp.name, quality=92)
        print(f"   ✂️  Cropped to {img.size[0]}×{img.size[1]} (4:5) for Instagram.")
        return tmp.name

def get_facebook_photo_url(photo_id, access_token):
    """Get the public URL of a Facebook photo."""
    url = f"{GRAPH_BASE}/{photo_id}"
    r = requests.get(url, params={
        "fields": "images",
        "access_token": access_token,
    })
    result = r.json()
    images = result.get("images", [])
    if images:
        # Use the largest image
        return images[0].get("source")
    return None

# ── Main agent logic ───────────────────────────────────────────────────────────

def run_agent():
    print(f"\n{'='*60}")
    print(f"Oslo Bike Tours Marketing Agent — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    config = load_config()
    state = load_state()

    SYSTEM_USER_TOKEN = config["META_ACCESS_TOKEN"]
    PAGE_ID = config["FACEBOOK_PAGE_ID"]
    IG_ACCOUNT_ID = config["INSTAGRAM_ACCOUNT_ID"]

    # Exchange system user token for a page access token (required for posting)
    print("\n🔑 Getting page access token...")
    ACCESS_TOKEN = get_page_access_token(SYSTEM_USER_TOKEN, PAGE_ID)
    if not ACCESS_TOKEN:
        print("⚠️  Could not get page access token. Check META_ACCESS_TOKEN in config.")
        return
    print(f"   ✅ Page token obtained.")

    # Check Gmail for new emails with attachments
    print("\n📬 Checking Gmail for new photos/videos...")

    gmail_token = get_gmail_token()
    if not gmail_token:
        print("⚠️  No GMAIL_ACCESS_TOKEN set. Set it via environment variable.")
        print("   Tip: Use the Gmail MCP or generate a token at Google Cloud Console.")
        return

    # Search for emails with attachments to the tours inbox
    messages = search_gmail_messages(
        f"to:{config['GMAIL_INBOX']} has:attachment newer_than:7d",
        max_results=10
    )

    if not messages:
        print("No new emails with attachments found.")
        return

    processed = set(state.get("processed", []))
    new_posts = 0

    for msg_meta in messages:
        msg_id = msg_meta["id"]

        if msg_id in processed:
            print(f"  ⏭️  Already processed: {msg_id}")
            continue

        print(f"\n📧 Processing message: {msg_id}")
        message = get_gmail_message(msg_id)
        if not message:
            continue

        subject = get_email_subject(message)
        body = get_email_body_text(message)
        attachments = extract_attachments(message)

        print(f"   Subject: {subject}")
        print(f"   Attachments: {len(attachments)}")

        if not attachments:
            print("   No media attachments found, skipping.")
            processed.add(msg_id)
            continue

        # Generate captions
        print("\n✍️  Generating captions with Claude...")
        filenames = [a["filename"] for a in attachments]
        captions = generate_captions(subject, body, filenames)

        if not captions:
            print("   ⚠️  Caption generation failed, using default.")
            captions = {
                "instagram": "🚲 Another amazing day exploring Oslo on bikes! Book your tour at oslobiketours.no\n\n#OsloBikeTours #Oslo #CyclingNorway #VisitOslo #BikeLife",
                "facebook": "🚲 An amazing day on the bikes in Oslo! Book your guided tour at oslobiketours.no"
            }

        print(f"   Instagram: {captions['instagram'][:80]}...")
        print(f"   Facebook:  {captions['facebook'][:80]}...")

        # Process each attachment
        for attachment in attachments:
            mime = attachment["mime_type"]
            is_image = mime.startswith("image/")
            is_video = mime.startswith("video/")

            if not (is_image or is_video):
                continue

            # Save to temp file
            with tempfile.NamedTemporaryFile(
                suffix=attachment["ext"], delete=False
            ) as tmp:
                tmp.write(attachment["data"])
                tmp_path = tmp.name

            try:
                print(f"\n📤 Posting: {attachment['filename']} ({mime})")

                # Post to Facebook
                fb_result = post_to_facebook(
                    PAGE_ID, ACCESS_TOKEN,
                    captions["facebook"],
                    image_path=tmp_path if is_image else None,
                    video_path=tmp_path if is_video else None,
                )

                # Post to Instagram (images only for now)
                if is_image and fb_result:
                    # Crop image to 4:5 ratio for Instagram
                    ig_path = crop_for_instagram(tmp_path)
                    ig_cleanup = ig_path != tmp_path  # True if a new file was created

                    try:
                        # Upload cropped image to Facebook (unpublished) to get a public URL
                        with open(ig_path, "rb") as f_ig:
                            ig_fb_r = requests.post(
                                f"{GRAPH_BASE}/{PAGE_ID}/photos",
                                data={"caption": captions["facebook"],
                                      "access_token": ACCESS_TOKEN,
                                      "published": "false"},
                                files={"source": f_ig}
                            )
                        ig_fb_data = ig_fb_r.json()
                        ig_photo_id = ig_fb_data.get("id")

                        if ig_photo_id:
                            time.sleep(2)
                            image_url = get_facebook_photo_url(ig_photo_id, ACCESS_TOKEN)
                            if image_url:
                                post_image_to_instagram(
                                    IG_ACCOUNT_ID, ACCESS_TOKEN,
                                    image_url, captions["instagram"]
                                )
                            else:
                                print("   ⚠️  Could not get cropped photo URL for Instagram.")
                        else:
                            print(f"   ⚠️  Instagram FB upload failed: {ig_fb_data}")
                    finally:
                        if ig_cleanup and os.path.exists(ig_path):
                            os.unlink(ig_path)

                new_posts += 1

            finally:
                os.unlink(tmp_path)

            # Only post the first valid attachment per email to avoid spam
            break

        processed.add(msg_id)
        state["processed"] = list(processed)
        save_state(state)

    print(f"\n✅ Done! Posted {new_posts} new post(s).")

if __name__ == "__main__":
    run_agent()
