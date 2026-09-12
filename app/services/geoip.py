from __future__ import annotations

import ipaddress
import logging
from functools import lru_cache

import geoip2.webservice
from geoip2.errors import GeoIP2Error

from app.config import settings
from app.services.phone import PhoneError, normalize_ksa_phone

log = logging.getLogger("mazaj.geoip")

GEO_BLOCKED = "geo_blocked"
VPN_BLOCKED = "vpn_blocked"
GEO_CHECK_FAILED = "geo_check_failed"


class GeoBlockError(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


def _is_production() -> bool:
    return settings.app_env.strip().lower() == "production"


@lru_cache(maxsize=1)
def _whitelist_e164() -> frozenset[str]:
    entries: set[str] = set()
    for raw in settings.geo_order_whitelist_phones.split(","):
        token = raw.strip()
        if not token:
            continue
        try:
            e164, _ = normalize_ksa_phone(token)
            entries.add(e164)
        except PhoneError:
            log.warning("geo_whitelist_invalid phone=***%s", token[-4:] if len(token) >= 4 else "????")
    return frozenset(entries)


def is_whitelisted_phone(phone_e164: str, phone_national: str) -> bool:
    allowed = _whitelist_e164()
    if not allowed:
        return False
    if phone_e164 in allowed:
        return True
    try:
        e164, _ = normalize_ksa_phone(phone_national)
        return e164 in allowed
    except PhoneError:
        return False


def _is_private_or_invalid_ip(ip: str) -> bool:
    if not ip:
        return True
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return True
    return addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved


def _suspicious_anonymizer(response: object) -> bool:
    anonymizer = getattr(response, "anonymizer", None)
    traits = getattr(response, "traits", None)

    def flag(obj: object | None, name: str) -> bool:
        return bool(getattr(obj, name, False)) if obj is not None else False

    checks = (
        "is_anonymous_vpn",
        "is_public_proxy",
        "is_tor_exit_node",
        "is_residential_proxy",
        "is_hosting_provider",
    )
    for check in checks:
        if flag(anonymizer, check) or flag(traits, check):
            return True
    return False


async def _lookup_insights(ip: str) -> object:
    async with geoip2.webservice.AsyncClient(
        settings.maxmind_account_id,
        settings.maxmind_license_key,
        timeout=5,
    ) as client:
        return await client.insights(ip)


async def check_order_geo(ip: str, phone_e164: str, phone_national: str) -> None:
    if is_whitelisted_phone(phone_e164, phone_national):
        log.info("geo_whitelist_bypass phone=***%s", phone_e164[-4:] if phone_e164 else "")
        return

    if _is_production() and not settings.geo_check_enabled:
        log.error("geo_check_disabled_in_production")
        raise GeoBlockError(GEO_CHECK_FAILED)

    if not settings.geo_check_enabled:
        log.info("geo_check_skipped env=%s", settings.app_env)
        return

    if not settings.maxmind_account_id or not settings.maxmind_license_key:
        if _is_production():
            log.error("geo_check_missing_credentials")
            raise GeoBlockError(GEO_CHECK_FAILED)
        log.warning("geo_check_skipped_missing_credentials env=%s", settings.app_env)
        return

    if _is_private_or_invalid_ip(ip):
        if _is_production():
            log.warning("geo_check_invalid_ip ip=%s", ip or "(empty)")
            raise GeoBlockError(GEO_CHECK_FAILED)
        log.info("geo_check_skipped_private_ip ip=%s env=%s", ip, settings.app_env)
        return

    try:
        response = await _lookup_insights(ip)
    except GeoIP2Error as exc:
        log.warning("geo_check_api_error ip=%s err=%s", ip, exc)
        raise GeoBlockError(GEO_CHECK_FAILED) from exc

    country = getattr(getattr(response, "country", None), "iso_code", None)
    if country != "SA":
        log.info("geo_blocked ip=%s country=%s", ip, country)
        raise GeoBlockError(GEO_BLOCKED)

    if _suspicious_anonymizer(response):
        log.info("vpn_blocked ip=%s", ip)
        raise GeoBlockError(VPN_BLOCKED)
