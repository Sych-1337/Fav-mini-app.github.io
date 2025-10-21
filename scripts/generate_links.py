from __future__ import annotations

import argparse
import base64
import os

BOT_USERNAME = os.getenv("BOT_USERNAME", "FavbetMini_bot")


def b64url(s: str) -> str:
    raw = s.encode("utf-8")
    enc = base64.urlsafe_b64encode(raw).decode("utf-8")
    return enc.rstrip("=")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Telegram deep links for /start and startapp")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--url", dest="full_url", type=str, help="Full https URL to open via startapp (will be base64url-encoded)")
    mode.add_argument("--triple", dest="triple", nargs=3, metavar=("ID","P2","L"), help="Triple id p2 l to encode into payload")
    args = parser.parse_args()

    print("Generated deep links:")
    if args.full_url:
        # base64url of full URL (Telegram-friendly chars only)
        enc = b64url(args.full_url)
        startapp_b64 = f"https://t.me/{BOT_USERNAME}/app?startapp={enc}"
        print("startapp (base64 of full URL):", startapp_b64)
    else:
        id_, p2, l = args.triple
        raw = f"{id_}_{p2}_{l}"
        encoded = b64url(f"{id_}:{p2}:{l}")
        start_raw = f"https://t.me/{BOT_USERNAME}?start={raw}"
        start_b64 = f"https://t.me/{BOT_USERNAME}?start={encoded}"
        startapp_raw = f"https://t.me/{BOT_USERNAME}/app?startapp={raw}"
        startapp_b64 = f"https://t.me/{BOT_USERNAME}/app?startapp={encoded}"
        print("/start (raw):     ", start_raw)
        print("/start (base64):  ", start_b64)
        print("startapp (raw):   ", startapp_raw)
        print("startapp (base64):", startapp_b64)


if __name__ == "__main__":
    main()
