#!/usr/bin/env python3
"""
poster_action.py — Écoute Ukraine autoposting engine (Telegram + Facebook + Instagram)

Built from the proven playbook (MajstorMe / Оновлена Україна experience).
Reads posts_queue.json, publishes due posts, marks them published, logs everything.

Env vars required:
  BOT_TOKEN              Telegram bot token
  CHANNEL_ID             Telegram channel id (e.g. -1001234567890)
  FB_PAGE_ACCESS_TOKEN   Facebook Page access token (long-lived, via /me/accounts)
  FB_PAGE_ID             Facebook Page ID (business page, NOT profile.php id)
  IG_USER_TOKEN          Instagram/Facebook long-lived user token (60 days)
  IG_ACCOUNT_ID          Instagram Business Account ID (instagram_business_account.id)
  TIMEZONE               e.g. "Europe/Paris" (default UTC)
  QUEUE_PATH             path to posts_queue.json (default "posts_queue.json")
  DRY_RUN                "1" to simulate without calling any real API
"""

import json
import os
import sys
import time
import datetime

import requests

try:
    import pytz
except ImportError:
    pytz = None

GRAPH_VERSION = "v21.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_VERSION}"

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")
FB_PAGE_ID = os.environ.get("FB_PAGE_ID")
IG_USER_TOKEN = os.environ.get("IG_USER_TOKEN")
IG_ACCOUNT_ID = os.environ.get("IG_ACCOUNT_ID")
TIMEZONE = os.environ.get("TIMEZONE", "UTC")
QUEUE_PATH = os.environ.get("QUEUE_PATH", "posts_queue.json")
DRY_RUN = os.environ.get("DRY_RUN", "0") == "1"


def log(msg):
    ts = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts} UTC] {msg}", flush=True)


def now_local():
    if pytz:
        tz = pytz.timezone(TIMEZONE)
        return datetime.datetime.now(tz).replace(tzinfo=None)
    return datetime.datetime.utcnow()


def load_queue():
    with open(QUEUE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_queue(queue):
    with open(QUEUE_PATH, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)


def is_due(post, now):
    """A post is due once, and only once. Once published=true it is never
    re-attempted automatically — see README for the manual retry procedure."""
    if post.get("published"):
        return False
    try:
        scheduled = datetime.datetime.strptime(post["scheduled_time"], "%Y-%m-%d %H:%M")
    except (KeyError, ValueError):
        log(f"Post id={post.get('id')} has invalid/missing scheduled_time, skipping.")
        return False
    return scheduled <= now


def safe_request(method, url, **kwargs):
    """Wraps requests calls: on failure, logs the actual response body
    (Meta/Telegram error payloads are the only useful debugging signal)."""
    try:
        r = requests.request(method, url, timeout=60, **kwargs)
        if not r.ok:
            log(f"HTTP {r.status_code} for {method} {url} -> {r.text}")
        return r
    except requests.RequestException as e:
        log(f"Request exception for {method} {url}: {e}")
        return None


# --------------------------------------------------------------------------
# Telegram
# --------------------------------------------------------------------------

def post_telegram(post):
    if DRY_RUN:
        log(f"[DRY_RUN] Would post to Telegram: id={post['id']}")
        return True

    text = post.get("tg_text", "")
    image_urls = post.get("image_urls") or ([post["image_url"]] if post.get("image_url") else [])

    try:
        if not image_urls:
            r = safe_request(
                "POST",
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": CHANNEL_ID, "text": text, "parse_mode": "HTML"},
            )
        elif len(image_urls) == 1:
            r = safe_request(
                "POST",
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                json={"chat_id": CHANNEL_ID, "photo": image_urls[0], "caption": text, "parse_mode": "HTML"},
            )
        else:
            media = [{"type": "photo", "media": url} for url in image_urls]
            media[0]["caption"] = text
            media[0]["parse_mode"] = "HTML"
            r = safe_request(
                "POST",
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMediaGroup",
                json={"chat_id": CHANNEL_ID, "media": media},
            )
        ok = bool(r is not None and r.ok and r.json().get("ok"))
        log(f"Telegram post id={post['id']}: {'OK' if ok else 'FAILED'}")
        return ok
    except Exception as e:
        log(f"Telegram post id={post['id']}: FAILED (exception: {e})")
        return False


# --------------------------------------------------------------------------
# Facebook
# --------------------------------------------------------------------------

def post_facebook(post):
    if DRY_RUN:
        log(f"[DRY_RUN] Would post to Facebook: id={post['id']}")
        return True

    text = post.get("fb_text", "")
    image_urls = post.get("image_urls") or ([post["image_url"]] if post.get("image_url") else [])

    try:
        if not image_urls:
            r = safe_request(
                "POST",
                f"{GRAPH_BASE}/{FB_PAGE_ID}/feed",
                data={"message": text, "access_token": FB_PAGE_ACCESS_TOKEN},
            )
        elif len(image_urls) == 1:
            r = safe_request(
                "POST",
                f"{GRAPH_BASE}/{FB_PAGE_ID}/photos",
                data={"url": image_urls[0], "caption": text, "access_token": FB_PAGE_ACCESS_TOKEN},
            )
        else:
            # Multi-photo post: upload each photo unpublished, then attach to one feed post.
            attached_media = []
            for url in image_urls:
                pr = safe_request(
                    "POST",
                    f"{GRAPH_BASE}/{FB_PAGE_ID}/photos",
                    data={"url": url, "published": "false", "access_token": FB_PAGE_ACCESS_TOKEN},
                )
                if pr is None or not pr.ok:
                    log(f"Facebook post id={post['id']}: FAILED (photo upload failed for {url})")
                    return False
                attached_media.append({"media_fbid": pr.json()["id"]})
            r = safe_request(
                "POST",
                f"{GRAPH_BASE}/{FB_PAGE_ID}/feed",
                data={
                    "message": text,
                    "attached_media": json.dumps(attached_media),
                    "access_token": FB_PAGE_ACCESS_TOKEN,
                },
            )
        ok = bool(r is not None and r.ok)
        log(f"Facebook post id={post['id']}: {'OK' if ok else 'FAILED'}")
        return ok
    except Exception as e:
        log(f"Facebook post id={post['id']}: FAILED (exception: {e})")
        return False


# --------------------------------------------------------------------------
# Instagram
# --------------------------------------------------------------------------

def ig_wait_ready(container_id, timeout=90, interval=3):
    """Poll a media container until status_code == FINISHED, or timeout."""
    elapsed = 0
    while elapsed < timeout:
        r = safe_request(
            "GET",
            f"{GRAPH_BASE}/{container_id}",
            params={"fields": "status_code", "access_token": IG_USER_TOKEN},
        )
        if r is not None and r.ok:
            status = r.json().get("status_code")
            if status == "FINISHED":
                return True
            if status == "ERROR":
                log(f"IG container {container_id}: status ERROR")
                return False
        time.sleep(interval)
        elapsed += interval
    log(f"IG container {container_id}: timed out waiting for FINISHED")
    return False


def post_instagram(post):
    if DRY_RUN:
        log(f"[DRY_RUN] Would post to Instagram: id={post['id']}")
        return True

    caption = post.get("ig_caption", "")
    hashtags = post.get("ig_hashtags", "")
    full_caption = f"{caption}\n\n{hashtags}".strip()

    ig_images = post.get("ig_image_urls") or (
        [post["ig_image_url"]] if post.get("ig_image_url") else
        (post.get("image_urls") or ([post["image_url"]] if post.get("image_url") else []))
    )
    if not ig_images:
        log(f"Instagram post id={post['id']}: FAILED (no image provided; IG requires an image)")
        return False

    try:
        if len(ig_images) == 1:
            cr = safe_request(
                "POST",
                f"{GRAPH_BASE}/{IG_ACCOUNT_ID}/media",
                data={"image_url": ig_images[0], "caption": full_caption, "access_token": IG_USER_TOKEN},
            )
            if cr is None or not cr.ok:
                log(f"Instagram post id={post['id']}: FAILED (container creation failed)")
                return False
            container_id = cr.json()["id"]
        else:
            # Carousel: create item containers, then a carousel container.
            item_ids = []
            for url in ig_images:
                ir = safe_request(
                    "POST",
                    f"{GRAPH_BASE}/{IG_ACCOUNT_ID}/media",
                    data={"image_url": url, "is_carousel_item": "true", "access_token": IG_USER_TOKEN},
                )
                if ir is None or not ir.ok:
                    log(f"Instagram post id={post['id']}: FAILED (carousel item failed for {url})")
                    return False
                item_ids.append(ir.json()["id"])
            cr = safe_request(
                "POST",
                f"{GRAPH_BASE}/{IG_ACCOUNT_ID}/media",
                data={
                    "media_type": "CAROUSEL",
                    "children": ",".join(item_ids),
                    "caption": full_caption,
                    "access_token": IG_USER_TOKEN,
                },
            )
            if cr is None or not cr.ok:
                log(f"Instagram post id={post['id']}: FAILED (carousel container failed)")
                return False
            container_id = cr.json()["id"]

        if not ig_wait_ready(container_id):
            log(f"Instagram post id={post['id']}: FAILED (container never finished processing)")
            return False

        pr = safe_request(
            "POST",
            f"{GRAPH_BASE}/{IG_ACCOUNT_ID}/media_publish",
            data={"creation_id": container_id, "access_token": IG_USER_TOKEN},
        )
        ok = bool(pr is not None and pr.ok)
        log(f"Instagram post id={post['id']}: {'OK' if ok else 'FAILED'}")
        return ok
    except Exception as e:
        log(f"Instagram post id={post['id']}: FAILED (exception: {e})")
        return False


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

PLATFORM_FUNCS = {
    "tg": post_telegram,
    "fb": post_facebook,
    "ig": post_instagram,
}


def main():
    now = now_local()
    log(f"Run started. Local time: {now.strftime('%Y-%m-%d %H:%M')} ({TIMEZONE}). DRY_RUN={DRY_RUN}")

    queue = load_queue()
    due_posts = [p for p in queue if is_due(p, now)]

    if not due_posts:
        log("no posts due right now")
        return

    changed = False
    for post in due_posts:
        log(f"Processing post id={post['id']} title=\"{post.get('title', '')}\" platforms={post.get('platforms')}")
        results = {}
        for platform in post.get("platforms", []):
            func = PLATFORM_FUNCS.get(platform)
            if not func:
                log(f"Unknown platform '{platform}' in post id={post['id']}, skipping it.")
                results[platform] = False
                continue
            results[platform] = func(post)

        post["published"] = True
        post["last_run_at"] = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        post["last_result"] = results
        changed = True

        failed = [p for p, ok in results.items() if not ok]
        if failed:
            log(
                f"Post id={post['id']}: some platforms FAILED ({failed}). "
                f"To retry only those platforms: set published=false and narrow "
                f"'platforms' to {failed} in {QUEUE_PATH}, then re-run."
            )

    if changed and not DRY_RUN:
        save_queue(queue)
        log(f"Queue updated and saved to {QUEUE_PATH}.")
    elif DRY_RUN:
        log("DRY_RUN active — queue not modified on disk.")


if __name__ == "__main__":
    sys.exit(main())
