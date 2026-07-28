#!/usr/bin/env python3
"""
get_long_token.py — one-off helper to exchange a short-lived Facebook user
token for a long-lived one (~60 days), and then fetch the Page token + IG
account id derived from it. Run this locally, NOT in GitHub Actions.

Usage:
  python get_long_token.py APP_ID APP_SECRET SHORT_LIVED_USER_TOKEN

It prints:
  IG_USER_TOKEN         (long-lived user token — put in GitHub Secrets)
  Available pages       (pick the right one by name/id)
  FB_PAGE_ACCESS_TOKEN  (for the page you choose — long-lived, inherits from user token)
  FB_PAGE_ID
  IG_ACCOUNT_ID         (if the page has a linked Instagram Business account)
"""

import sys
import requests

GRAPH_VERSION = "v21.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_VERSION}"


def main():
    if len(sys.argv) != 4:
        print("Usage: python get_long_token.py APP_ID APP_SECRET SHORT_LIVED_USER_TOKEN")
        sys.exit(1)

    app_id, app_secret, short_token = sys.argv[1], sys.argv[2], sys.argv[3]

    r = requests.get(
        f"{GRAPH_BASE}/oauth/access_token",
        params={
            "grant_type": "fb_exchange_token",
            "client_id": app_id,
            "client_secret": app_secret,
            "fb_exchange_token": short_token,
        },
        timeout=30,
    )
    r.raise_for_status()
    long_token = r.json()["access_token"]
    print(f"\nIG_USER_TOKEN (long-lived, ~60 days):\n{long_token}\n")

    r2 = requests.get(f"{GRAPH_BASE}/me/accounts", params={"access_token": long_token}, timeout=30)
    r2.raise_for_status()
    pages = r2.json().get("data", [])

    if not pages:
        print("No pages found for this user token. Check that the account admins a Facebook Page.")
        return

    print("Pages found (verify by App ID / name — accounts with several apps can list unrelated pages):\n")
    for p in pages:
        print(f"  name={p.get('name')!r}  id={p.get('id')}  access_token={p.get('access_token')}")

    print("\nFor each page above that you want to use:")
    print(f"  FB_PAGE_ID = <that page's id>")
    print(f"  FB_PAGE_ACCESS_TOKEN = <that page's access_token>")
    print("\nThen fetch IG_ACCOUNT_ID with:")
    print(
        f'  curl "{GRAPH_BASE}/<FB_PAGE_ID>?fields=instagram_business_account&access_token=<FB_PAGE_ACCESS_TOKEN>"'
    )
    print("  -> take instagram_business_account.id (NOT the page's own id)")


if __name__ == "__main__":
    main()
