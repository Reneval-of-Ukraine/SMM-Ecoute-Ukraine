#!/usr/bin/env python3
"""
build_queue.py — walks Month_1/ and auto-generates posts_queue.json for the
tg/fb/ig autoposting pipeline.

Scope / exclusions (deliberate):
  - LinkedIn and WhatsApp folders are skipped entirely — poster_action.py
    does not publish there (separate mechanics, see README).
  - Folders whose name starts with STORY- are skipped — Instagram/Facebook
    Stories need a different API call (media_type=STORIES) not yet
    implemented in poster_action.py.
  - Folders whose name starts with VIDEO- are skipped — video publishing
    needs a different upload flow (video_url + longer polling) not yet
    implemented in poster_action.py.
  - Mixed_Bridge/Facebook is included (channel = fb).

Text extraction: each caption.md is split on markdown headers (lines
starting with one or more '#'). Section titles are matched case-insensitively
against keywords to find the Instagram / Telegram / Facebook caption body and
the hashtags block. Caption.md templates were NOT perfectly consistent across
the whole pack (some say "# 1. Final Instagram caption", others "## 1.
Instagram caption — final") — this parser matches on keywords, not exact
header text, specifically to tolerate that drift. Spot-check the output.
"""

import json
import os
import re
import sys
from datetime import datetime, timedelta

ROOT = sys.argv[1] if len(sys.argv) > 1 else "Month_1"
OUT_PATH = sys.argv[2] if len(sys.argv) > 2 else "posts_queue_full.json"
REPO = sys.argv[3] if len(sys.argv) > 3 else "Reneval-of-Ukraine/SMM-Ecoute-Ukraine"
START_DATE = datetime.strptime(sys.argv[4], "%Y-%m-%d") if len(sys.argv) > 4 else datetime(2026, 8, 3)

RAW_BASE = f"https://raw.githubusercontent.com/{REPO}/main/images"

SKIP_DIR_NAMES = {"LinkedIn", "WhatsApp"}
SKIP_FOLDER_MARKERS = ("STORY-", "VIDEO-")


def find_content_folders(root):
    """Yield (channel, folder_path) for every leaf content folder under
    Month_1, skipping LinkedIn/WhatsApp/Stories/Videos."""
    for audience_dir in sorted(os.listdir(root)):
        audience_path = os.path.join(root, audience_dir)
        if not os.path.isdir(audience_path):
            continue
        for channel_dir in sorted(os.listdir(audience_path)):
            if channel_dir in SKIP_DIR_NAMES:
                continue
            channel_path = os.path.join(audience_path, channel_dir)
            if not os.path.isdir(channel_path):
                continue
            channel = {"Instagram": "ig", "Telegram": "tg", "Facebook": "fb"}.get(channel_dir)
            if channel is None:
                continue
            for folder_name in sorted(os.listdir(channel_path)):
                folder_path = os.path.join(channel_path, folder_name)
                if not os.path.isdir(folder_path):
                    continue
                if any(marker in folder_name for marker in SKIP_FOLDER_MARKERS):
                    continue
                yield channel, folder_path, folder_name


def split_sections(md_text):
    """Split a caption.md body into {header_text: body_text} by header lines."""
    lines = md_text.splitlines()
    sections = {}
    current_header = None
    buf = []
    for line in lines:
        # Require whitespace after the hashes (real markdown headers do) so
        # that a hashtag line like "#ÉcouteUkraine #підтримка" is NOT
        # mistaken for a new section header.
        m = re.match(r'^#{1,3}\s+(.+)$', line.strip())
        if m:
            if current_header is not None:
                sections[current_header] = "\n".join(buf).strip()
            current_header = m.group(1).strip().lower()
            buf = []
        else:
            buf.append(line)
    if current_header is not None:
        sections[current_header] = "\n".join(buf).strip()
    return sections


def clean_body(text):
    # Strip a leading/trailing code fence if the section is wrapped in ```text ... ```
    text = re.sub(r'^```(?:text)?\s*\n', '', text.strip())
    text = re.sub(r'\n```$', '', text)
    return text.strip()


def pick_section(sections, must_include, must_exclude=()):
    for header, body in sections.items():
        if any(x in header for x in must_include) and not any(x in header for x in must_exclude):
            if body:
                return clean_body(body)
    return None


def extract_caption_fields(caption_path, channel):
    with open(caption_path, "r", encoding="utf-8") as f:
        text = f.read()
    sections = split_sections(text)

    result = {}
    if channel == "ig":
        result["ig_caption"] = pick_section(sections, ["instagram"], ["short", "hashtag", "alt text"])
        result["ig_hashtags"] = pick_section(sections, ["hashtag"])
    elif channel == "tg":
        result["tg_text"] = pick_section(sections, ["telegram"], ["short", "visual"])
    elif channel == "fb":
        result["fb_text"] = pick_section(
            sections,
            ["facebook", "основний текст", "основной текст"],
            ["short", "cta", "visual", "скорочен", "сокращ", "візуал", "визуал", "хештег", "хэштег"],
        )
    return result


def find_images(folder_path, channel):
    visuals_dir = os.path.join(folder_path, "visuals")
    search_dir = visuals_dir if os.path.isdir(visuals_dir) else folder_path
    images = []
    for f in sorted(os.listdir(search_dir)):
        if f.lower().endswith((".png", ".jpg", ".jpeg")):
            images.append(os.path.join(search_dir, f))
    return images


def content_id_from_folder(folder_name):
    # Folder names look like "UA-01_Koly_tryvoha_nakryvaie" or "FB-UA-01_..."
    m = re.match(r'^([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)_', folder_name)
    return m.group(1) if m else folder_name


def main():
    entries = []
    skipped = []

    # Round-robin scheduling: spread posts across weekdays, ~1 per channel-slot per day,
    # honoring roughly the cadence from the master base (ig 3x/wk, tg 4-5x/wk, fb 3-4x/wk).
    channel_cursors = {"ig": 0, "tg": 0, "fb": 0}
    channel_days_per_week = {"ig": [0, 2, 4], "tg": [0, 1, 2, 3, 5], "fb": [1, 3, 5]}  # Mon=0

    grouped = {"ig": [], "tg": [], "fb": []}

    for channel, folder_path, folder_name in find_content_folders(ROOT):
        caption_files = [f for f in os.listdir(folder_path) if f.endswith("_caption.md")]
        if not caption_files:
            skipped.append((folder_path, "no *_caption.md file found"))
            continue
        if any(marker in caption_files[0] for marker in SKIP_FOLDER_MARKERS):
            skipped.append((folder_path, f"caption file {caption_files[0]} is a Story/Video asset, not a feed post"))
            continue
        caption_path = os.path.join(folder_path, caption_files[0])
        fields = extract_caption_fields(caption_path, channel)

        text_key = {"ig": "ig_caption", "tg": "tg_text", "fb": "fb_text"}[channel]
        if not fields.get(text_key):
            skipped.append((folder_path, f"could not extract {text_key} from {caption_files[0]}"))
            continue

        images = find_images(folder_path, channel)
        if not images:
            skipped.append((folder_path, "no image files found"))
            continue

        content_id = content_id_from_folder(folder_name)
        rel_images = [
            f"{RAW_BASE}/{content_id}/{os.path.basename(p)}" for p in images
        ]

        entry = {
            "content_id": content_id,
            "title": f"{content_id} — {folder_name[len(content_id) + 1:].replace('_', ' ')}",
            "platforms": [channel],
            "published": False,
        }
        if channel == "ig":
            entry["ig_image_urls"] = rel_images
            entry["ig_caption"] = fields["ig_caption"]
            entry["ig_hashtags"] = fields.get("ig_hashtags") or ""
        else:
            entry["image_url"] = rel_images[0]
            entry[text_key] = fields[text_key]

        grouped[channel].append(entry)

    # Assign scheduled_time by walking forward day by day, filling each
    # channel's designated weekdays in order.
    day_offset = 0
    max_days = 40
    remaining = {c: list(items) for c, items in grouped.items()}
    while any(remaining.values()) and day_offset < max_days:
        current_date = START_DATE + timedelta(days=day_offset)
        weekday = current_date.weekday()
        for channel, hour in (("ig", 10), ("tg", 9), ("fb", 15)):
            if weekday in channel_days_per_week[channel] and remaining[channel]:
                entry = remaining[channel].pop(0)
                entry["scheduled_time"] = current_date.strftime("%Y-%m-%d") + f" {hour:02d}:00"
                entries.append(entry)
        day_offset += 1

    entries.sort(key=lambda e: e["scheduled_time"])
    for i, e in enumerate(entries, start=1):
        e["id"] = i
        e.pop("content_id", None)

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(entries)} posts to {OUT_PATH}")
    print(f"Skipped {len(skipped)} folders:")
    for path, reason in skipped:
        print(f"  - {path}: {reason}")


if __name__ == "__main__":
    main()
