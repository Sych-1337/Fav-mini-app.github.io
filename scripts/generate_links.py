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
    parser.add_argument("id", type=str)
    parser.add_argument("p2", type=str)
    parser.add_argument("l", type=str)
    args = parser.parse_args()

    id_, p2, l = args.id, args.p2, args.l

    # raw underscore form
    raw = f"{id_}_{p2}_{l}"
    # base64url("id:p2:l")
    encoded = b64url(f"{id_}:{p2}:{l}")

    start_raw = f"https://t.me/{BOT_USERNAME}?start={raw}"
    start_b64 = f"https://t.me/{BOT_USERNAME}?start={encoded}"

    startapp_raw = f"https://t.me/{BOT_USERNAME}/app?startapp={raw}"
    startapp_b64 = f"https://t.me/{BOT_USERNAME}/app?startapp={encoded}"

    print("Generated deep links:")
    print("/start (raw):     ", start_raw)
    print("/start (base64):  ", start_b64)
    print("startapp (raw):   ", startapp_raw)
    print("startapp (base64):", startapp_b64)


if __name__ == "__main__":
    main()
