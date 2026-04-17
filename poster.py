#!/usr/bin/env python3
"""
Oslo Bike Tours – Social Media Auto-Poster
==========================================
Polls the Gmail inbox for new tour photo emails, downloads attachments,
generates a marketing caption using Claude, and posts to Facebook (and
optionally Instagram when an IG Business account is connected).

Requirements:
    pip3 install google-auth google-auth-oauthlib google-auth-httplib2 \
                 google-api-python-client requests anthropic pillow

Usage:
    python3 poster.py          # run once (checks for new emails)
    python3 poster.py --test   # test-post using the latest image in images/
"""

import os
import sys
import json
import base64
import hashlib
import logging
import argparse
import mimetypes
from datetime import datetime
from pathlib import Path

import requests

# ── Configuration ──────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "config.json"
PROCESSED_FILE = SCRIPT_DIR / "processed_messages.json"
IMAGES_DIR = SCRIPT_DIR / "images"
LOG_FILE = SCRIPT_DIR / "run_log.md"

IMAGES_DIR.mkdir(exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def load_config():
    with open(CONFIG_FILE) as f:
        return json.load(f)


def load_processed():
    if PROCESSED_FILE.exists():
        with open(PROCESSED_FILE) as f:
            return set(json.load(f).get("processed", []))
    return set()


def save_processed(processed_set):
    with open(PROCESSED_FILE, "w") as f:
        json.dump({"processed": list(processed_set)}, f, indent=2)


def append_log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"\n### {timestamp}\n{message}\n")
    log.info(message)


# ── Gmail (via Google API) ──────────────────────────────────────────────────────

def get_gmail_service():
    """Build an authenticated Gmail API service using OAuth2 credentials."""
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
    creds_file = SCRIPT_DIR / "gmail_token.json"
    oauth_creds_file = SCRIPT_DIR / "gmail_credentials.json"

    creds = None
    if creds_file.exists():
        creds = Credentials.from_authorized_user_file(str(creds_file), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not oauth_creds_file.exists():
                raise FileNotFoundError(
                    f"Gmail OAuth credentials not found at {oauth_creds_file}. "
                    "Download from Google Cloud Console → APIs & Services → Credentials "
                    "and save as gmail_credentials.json"
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(oauth_creds_file), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(creds_file, "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def fetch_new_photo_emails(cfg, processed):
    """Return list of (message_id, [(filename, bytes)]) for new emails with image attachments."""
    service = get_gmail_service()
    results = service.users().messages().list(
        userId="me",
        q="has:attachment",
        maxResults=20
    ).execute()

    messages = results.get("messages", [])
    new_items = []

    for msg_meta in messages:
        msg_id = msg_meta["id"]
        if msg_id in processed:
            continue

        msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
        attachments = []

        def walk_parts(parts):
            for part in parts:
                if part.get("parts"):
                    walk_parts(part["parts"])
                if part.get("filename") and part.get("body", {}).get("attachmentId"):
                    mime = part.get("mimeType", "")
                    if mime.startswith("image/"):
                        att_id = part["body"]["attachmentId"]
                        att = service.users().messages().attachments().get(
                            userId="me", messageId=msg_id, id=att_id
                        ).execute()
                        data = base64.urlsafe_b64decode(att["data"])
                        attachments.append((part["filename"], data))

        payload = msg.get("payload", {})
        if payload.get("parts"):
            walk_parts(payload["parts"])

        if attachments:
            new_items.append((msg_id, attachments))

    return new_items


def save_attachments(attachments):
    """Save image bytes to disk, return list of saved file paths."""
    saved = []
    for filename, data in attachments:
        safe_name = "".join(c for c in filename if c.isalnum() or c in "._-")
        dest = IMAGES_DIR / safe_name
        # Avoid overwriting with a content hash suffix
        if dest.exists():
            h = hashlib.md5(data).hexdigest()[:6]
            stem, ext = os.path.splitext(safe_name)
            dest = IMAGES_DIR / f"{stem}_{h}{ext}"
        with open(dest, "wb") as f:
            f.write(data)
        saved.append(dest)
        log.info(f"Saved attachment: {dest}")
    return saved


# ── Caption Generation (Claude) ────────────────────────────────────────────────

def generate_caption(image_path: Path) -> str:
    """Generate a social media caption for the image using Claude."""
    try:
        import anthropic

        client = anthropic.Anthropic()

        with open(image_path, "rb") as f:
            image_data = base64.standard_b64encode(f.read()).decode("utf-8")

        ext = image_path.suffix.lower()
        mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                    ".png": "image/png", ".gif": "image/gif", ".webp": "image/webp"}
        media_type = mime_map.get(ext, "image/jpeg")

        msg = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=512,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "You are the voice of Oslo Bike Tours on social media. "
                            "Your style is authentic, curious, and local — like a knowledgeable friend "
                            "who knows Oslo inside out and loves sharing it. "
                            "\n\n"
                            "Look at this photo and write a short, interesting social media post about it. "
                            "Focus on: what's happening in the scene, something specific and genuine about "
                            "Oslo or Norwegian cycling culture, a local detail, a seasonal observation, "
                            "or a story the image suggests. "
                            "\n\n"
                            "Rules:\n"
                            "- Do NOT write promotional or salesy language (no 'Book now!', no 'Join us', "
                            "no 'Don't miss out')\n"
                            "- Do NOT include website links or calls-to-action\n"
                            "- Keep it under 150 words — short and punchy is better\n"
                            "- 1-2 emojis max, only if natural\n"
                            "- End with 4-6 relevant hashtags on a separate line\n"
                            "- Write in English\n"
                            "- Tone: warm, genuine, slightly witty — never corporate"
                        ),
                    },
                ],
            }],
        )
        return msg.content[0].text.strip()

    except Exception as e:
        log.warning(f"Claude caption generation failed: {e}. Using default caption.")
        return (
            "Oslo looks different at 15 km/h. You notice things you'd never catch from a bus window — "
            "the old harbour warehouses, the smell of the fjord, someone's cat watching from a window ledge.\n\n"
            "#OsloBikeTours #CyclingOslo #VisitOslo #Oslo #NorwayLife #BikeLife"
        )


# ── Meta Graph API Posting ─────────────────────────────────────────────────────

GRAPH_BASE = "https://graph.facebook.com/v25.0"


def upload_photo_to_facebook(image_path: Path, caption: str, page_id: str, page_token: str) -> str:
    """Upload a photo with caption to the Facebook Page. Returns the post ID."""
    url = f"{GRAPH_BASE}/{page_id}/photos"
    with open(image_path, "rb") as f:
        files = {"source": (image_path.name, f, "image/jpeg")}
        data = {
            "caption": caption,
            "access_token": page_token,
        }
        resp = requests.post(url, data=data, files=files, timeout=60)

    result = resp.json()
    if "error" in result:
        raise RuntimeError(f"Facebook photo upload failed: {result['error']}")

    post_id = result.get("post_id") or result.get("id")
    log.info(f"Facebook post created: {post_id}")
    return post_id


def post_to_instagram(image_path: Path, caption: str, ig_account_id: str, page_token: str) -> str:
    """
    Two-step Instagram media publish:
    1. Upload image as unpublished FB photo → get CDN URL
    2. Create IG container with that URL → publish
    Returns the Instagram media ID.
    """
    page_id_from_token_resp = requests.get(
        f"{GRAPH_BASE}/me?fields=id&access_token={page_token}"
    ).json()
    page_id = page_id_from_token_resp.get("id")

    # Step 1: upload as unpublished FB photo to get CDN URL
    url = f"{GRAPH_BASE}/{page_id}/photos"
    with open(image_path, "rb") as f:
        files = {"source": (image_path.name, f, "image/jpeg")}
        data = {
            "published": "false",
            "access_token": page_token,
        }
        resp = requests.post(url, data=data, files=files, timeout=60)
    result = resp.json()
    if "error" in result:
        raise RuntimeError(f"FB unpublished upload failed: {result['error']}")
    fb_photo_id = result["id"]

    # Get CDN URL for this unpublished photo
    cdn_resp = requests.get(
        f"{GRAPH_BASE}/{fb_photo_id}?fields=images&access_token={page_token}"
    ).json()
    if "error" in cdn_resp:
        raise RuntimeError(f"Could not get CDN URL: {cdn_resp['error']}")
    image_url = cdn_resp["images"][0]["source"]

    # Step 2: Create IG container
    container_resp = requests.post(
        f"{GRAPH_BASE}/{ig_account_id}/media",
        data={
            "image_url": image_url,
            "caption": caption,
            "access_token": page_token,
        },
        timeout=60,
    ).json()
    if "error" in container_resp:
        raise RuntimeError(f"IG container creation failed: {container_resp['error']}")
    creation_id = container_resp["id"]

    # Step 3: Wait for container to be ready, then publish
    import time
    for attempt in range(12):  # poll up to ~60 seconds
        status_resp = requests.get(
            f"{GRAPH_BASE}/{creation_id}?fields=status_code&access_token={page_token}",
            timeout=30,
        ).json()
        status = status_resp.get("status_code", "")
        log.info(f"IG container status (attempt {attempt + 1}): {status}")
        if status == "FINISHED":
            break
        if status == "ERROR":
            raise RuntimeError(f"IG container processing failed: {status_resp}")
        time.sleep(5)
    else:
        raise RuntimeError("IG container never reached FINISHED status after 60s")

    publish_resp = requests.post(
        f"{GRAPH_BASE}/{ig_account_id}/media_publish",
        data={
            "creation_id": creation_id,
            "access_token": page_token,
        },
        timeout=60,
    ).json()
    if "error" in publish_resp:
        raise RuntimeError(f"IG publish failed: {publish_resp['error']}")

    media_id = publish_resp["id"]
    log.info(f"Instagram post created: {media_id}")
    return media_id


# ── Main Orchestration ─────────────────────────────────────────────────────────

def process_email(msg_id, attachments_raw, cfg, processed):
    """Download attachments, generate caption, post to social media."""
    saved_paths = save_attachments(attachments_raw)
    if not saved_paths:
        log.info(f"No image attachments in {msg_id}, skipping.")
        processed.add(msg_id)
        return

    # Use the first (or best) image — prefer largest file if multiple
    image_path = max(saved_paths, key=lambda p: p.stat().st_size)
    log.info(f"Generating caption for {image_path.name}...")
    caption = generate_caption(image_path)

    page_id = cfg["page_id"]
    page_token = cfg["page_access_token"]
    ig_id = cfg.get("instagram_account_id")

    results = {}

    # Post to Facebook
    try:
        fb_post_id = upload_photo_to_facebook(image_path, caption, page_id, page_token)
        results["facebook"] = fb_post_id
        append_log(
            f"✅ Facebook post: https://www.facebook.com/{fb_post_id}\n"
            f"Image: {image_path.name}\n"
            f"Caption preview: {caption[:100]}..."
        )
    except Exception as e:
        results["facebook_error"] = str(e)
        append_log(f"❌ Facebook post FAILED for {image_path.name}: {e}")

    # Post to Instagram (if connected)
    if ig_id:
        try:
            ig_media_id = post_to_instagram(image_path, caption, ig_id, page_token)
            results["instagram"] = ig_media_id
            append_log(f"✅ Instagram post: {ig_media_id}")
        except Exception as e:
            results["instagram_error"] = str(e)
            append_log(f"❌ Instagram post FAILED: {e}")
    else:
        log.info("Instagram account not configured — skipping Instagram post.")
        append_log("ℹ️ Instagram skipped (no account connected to Facebook page yet).")

    processed.add(msg_id)
    return results


def run_once(test_mode=False):
    cfg = load_config()
    processed = load_processed()

    if test_mode:
        # Pick the most recent image in images/ and post it
        images = sorted(IMAGES_DIR.glob("*.jpg")) + sorted(IMAGES_DIR.glob("*.jpeg")) + sorted(IMAGES_DIR.glob("*.png"))
        if not images:
            print("No images found in images/ folder for test mode.")
            return
        image_path = images[-1]
        print(f"TEST MODE: posting {image_path.name}")
        caption = generate_caption(image_path)
        print(f"Caption:\n{caption}\n")
        page_id = cfg["page_id"]
        page_token = cfg["page_access_token"]
        ig_id = cfg.get("instagram_account_id")

        try:
            post_id = upload_photo_to_facebook(image_path, caption, page_id, page_token)
            print(f"✅ Facebook post created: https://www.facebook.com/{post_id}")
        except Exception as e:
            print(f"❌ Facebook post FAILED: {e}")

        if ig_id:
            try:
                ig_media_id = post_to_instagram(image_path, caption, ig_id, page_token)
                print(f"✅ Instagram post created: {ig_media_id}")
            except Exception as e:
                print(f"❌ Instagram post FAILED: {e}")
        else:
            print("⚠️  Instagram skipped (no instagram_account_id in config)")
        return

    # Normal mode: check Gmail for new photo emails
    append_log("🔍 Checking for new tour photo emails...")

    try:
        new_emails = fetch_new_photo_emails(cfg, processed)
    except FileNotFoundError as e:
        append_log(f"⚠️ Gmail setup needed: {e}")
        print(f"\nGmail OAuth setup required. See instructions below.\n{e}")
        return
    except Exception as e:
        append_log(f"❌ Gmail fetch error: {e}")
        log.error(f"Gmail error: {e}", exc_info=True)
        return

    if not new_emails:
        append_log("📭 No new photo emails found.")
        return

    append_log(f"📬 Found {len(new_emails)} new email(s) with photos.")

    for msg_id, attachments in new_emails:
        try:
            process_email(msg_id, attachments, cfg, processed)
        except Exception as e:
            append_log(f"❌ Error processing message {msg_id}: {e}")
            log.error(f"Error processing {msg_id}", exc_info=True)
            processed.add(msg_id)  # mark as processed to avoid retry loop

    save_processed(processed)
    append_log("✅ Run complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Oslo Bike Tours auto-poster")
    parser.add_argument("--test", action="store_true", help="Post most recent image in images/ as a test")
    args = parser.parse_args()
    run_once(test_mode=args.test)
