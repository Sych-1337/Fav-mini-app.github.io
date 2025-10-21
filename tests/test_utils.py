from __future__ import annotations

import base64
import os
import pytest

from bot_v3.utils import decode_payload, build_target_url


def b64url(s: str) -> str:
    return base64.urlsafe_b64encode(s.encode()).decode().rstrip("=")


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("330_126_640", ("330", "126", "640")),
        (b64url("330:126:640"), ("330", "126", "640")),
        ("1_2_3", ("1", "2", "3")),
        (b64url("1:2:3"), ("1", "2", "3")),
    ],
)
def test_decode_ok(raw: str, expected: tuple[str, str, str]) -> None:
    assert decode_payload(raw) == expected


def test_decode_non_numeric() -> None:
    with pytest.raises(ValueError):
        decode_payload("330_abc_640")
    with pytest.raises(ValueError):
        decode_payload(b64url("330:abc:640"))


def test_decode_bad_format() -> None:
    with pytest.raises(ValueError):
        decode_payload("330_126")  # not 3 parts
    with pytest.raises(ValueError):
        decode_payload(b64url("330:126"))  # not 3 parts


def test_decode_bad_b64() -> None:
    with pytest.raises(ValueError):
        decode_payload("@@@notb64@@@")


def test_payload_length_limit() -> None:
    long = "1" * 65
    with pytest.raises(ValueError):
        decode_payload(long)


def test_build_target_url_domain_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALLOWED_REDIRECT_DOMAIN", "evil.example")
    # Should still enforce default allowed domain from utils
    url = build_target_url("330", "126", "640")
    assert url.startswith("https://go.favbet.ua/")
    assert url.endswith("/330/126?l=640".replace("/330/126", "/330/126"))


def test_build_target_url_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALLOWED_REDIRECT_DOMAIN", "go.favbet.ua")
    url = build_target_url("330", "126", "640")
    assert url == "https://go.favbet.ua/330/126?l=640"
