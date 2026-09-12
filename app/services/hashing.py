from __future__ import annotations

import hashlib


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def digits_country(e164: str) -> str:
    return "".join(ch for ch in e164 if ch.isdigit())


def meta_snap_phone_hash(e164: str) -> str:
    """Meta and Snap: digits only, no plus, then SHA-256."""
    return sha256_hex(digits_country(e164))


def tiktok_phone_hash(e164: str) -> str:
    """TikTok: plus-prefixed E.164 then SHA-256."""
    return sha256_hex("+" + digits_country(e164))


def name_hash(name: str) -> str:
    return sha256_hex(name.strip().lower())


def country_hash() -> str:
    return sha256_hex("sa")


def external_id_hash(e164: str) -> str:
    return sha256_hex(e164)
