from __future__ import annotations

import base64
import logging
import os
from typing import Tuple

logger = logging.getLogger(__name__)

ALLOWED_REDIRECT_DOMAIN = os.getenv("ALLOWED_REDIRECT_DOMAIN", "go.favbet.ua")


def decode_payload(payload: str) -> Tuple[str, str, str]:
    """
    Supported formats:
    - raw underscore: "id_p2_l" (e.g., "330_126_640")
    - base64url("id:p2:l")
    Returns tuple of strings (id, p2, l). Raises ValueError on invalid input.
    """
    if not payload:
        raise ValueError("Пустой payload")

    # Telegram ограничивает payload 64 байтами
    if len(payload.encode("utf-8")) > 64:
        raise ValueError("Payload превышает 64 байта")

    id_str: str
    p2_str: str
    l_str: str

    if "_" in payload:
        parts = payload.split("_")
        if len(parts) != 3:
            raise ValueError("Некорректный формат payload: ожидается id_p2_l")
        id_str, p2_str, l_str = parts
    else:
        # try base64url decode to str "id:p2:l"
        try:
            # add missing padding for urlsafe b64
            pad = '=' * (-len(payload) % 4)
            decoded = base64.urlsafe_b64decode(payload + pad).decode("utf-8")
        except Exception as e:
            raise ValueError("Некорректная base64url строка") from e
        parts = decoded.split(":")
        if len(parts) != 3:
            raise ValueError("Некорректный формат расшифровки: ожидается 'id:p2:l'")
        id_str, p2_str, l_str = parts

    # validate numeric
    if not (id_str.isdigit() and p2_str.isdigit() and l_str.isdigit()):
        raise ValueError("Параметры должны быть числами: id, p2 и l")

    return id_str, p2_str, l_str


def build_target_url(id_str: str, p2_str: str, l_str: str) -> str:
    """Build https://{domain}/{id}/{p2}?l={l} with domain safety check."""
    env_domain = os.getenv("ALLOWED_REDIRECT_DOMAIN", ALLOWED_REDIRECT_DOMAIN)
    # Разрешаем только точное совпадение с дефолтом, чтобы избежать подмены
    domain = ALLOWED_REDIRECT_DOMAIN if env_domain != ALLOWED_REDIRECT_DOMAIN else env_domain
    return f"https://{domain}/{id_str}/{p2_str}?l={l_str}"
