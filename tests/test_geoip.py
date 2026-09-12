from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.geoip import (
    GEO_BLOCKED,
    GEO_CHECK_FAILED,
    VPN_BLOCKED,
    GeoBlockError,
    _whitelist_e164,
    check_order_geo,
    is_whitelisted_phone,
)
from app.services.phone import normalize_ksa_phone


@pytest.fixture(autouse=True)
def clear_whitelist_cache() -> None:
    _whitelist_e164.cache_clear()
    yield
    _whitelist_e164.cache_clear()


def _settings(monkeypatch: pytest.MonkeyPatch, **kwargs: object) -> None:
    from app.config import settings

    for key, value in kwargs.items():
        monkeypatch.setattr(settings, key, value)


def _mock_insights(monkeypatch: pytest.MonkeyPatch, response: object) -> None:
    async def fake_lookup(ip: str) -> object:
        return response

    monkeypatch.setattr("app.services.geoip._lookup_insights", fake_lookup)


def _insights_response(
    country: str = "SA",
    *,
    vpn: bool = False,
    proxy: bool = False,
    tor: bool = False,
    residential: bool = False,
    hosting: bool = False,
) -> SimpleNamespace:
    anonymizer = SimpleNamespace(
        is_anonymous_vpn=vpn,
        is_public_proxy=proxy,
        is_tor_exit_node=tor,
        is_residential_proxy=residential,
        is_hosting_provider=hosting,
    )
    return SimpleNamespace(
        country=SimpleNamespace(iso_code=country),
        anonymizer=anonymizer,
        traits=SimpleNamespace(),
    )


def test_whitelist_phone_matches() -> None:
    e164, national = normalize_ksa_phone("0550603022")
    assert is_whitelisted_phone(e164, national)


@pytest.mark.asyncio
async def test_whitelist_bypasses_non_sa_ip(monkeypatch: pytest.MonkeyPatch) -> None:
    _settings(
        monkeypatch,
        app_env="production",
        geo_check_enabled=True,
        maxmind_account_id="1",
        maxmind_license_key="key",
        geo_order_whitelist_phones="0550603022",
    )
    _mock_insights(monkeypatch, _insights_response("US", vpn=True))
    e164, national = normalize_ksa_phone("0550603022")
    await check_order_geo("8.8.8.8", e164, national)


@pytest.mark.asyncio
async def test_non_whitelisted_non_sa_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    _settings(
        monkeypatch,
        app_env="production",
        geo_check_enabled=True,
        maxmind_account_id="1",
        maxmind_license_key="key",
        geo_order_whitelist_phones="",
    )
    _mock_insights(monkeypatch, _insights_response("US"))
    e164, national = normalize_ksa_phone("0501234567")
    with pytest.raises(GeoBlockError) as exc:
        await check_order_geo("8.8.8.8", e164, national)
    assert exc.value.reason == GEO_BLOCKED


@pytest.mark.asyncio
async def test_non_whitelisted_sa_vpn_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    _settings(
        monkeypatch,
        app_env="production",
        geo_check_enabled=True,
        maxmind_account_id="1",
        maxmind_license_key="key",
        geo_order_whitelist_phones="",
    )
    _mock_insights(monkeypatch, _insights_response("SA", vpn=True))
    e164, national = normalize_ksa_phone("0501234567")
    with pytest.raises(GeoBlockError) as exc:
        await check_order_geo("1.2.3.4", e164, national)
    assert exc.value.reason == VPN_BLOCKED


@pytest.mark.asyncio
async def test_non_whitelisted_sa_clean_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    _settings(
        monkeypatch,
        app_env="production",
        geo_check_enabled=True,
        maxmind_account_id="1",
        maxmind_license_key="key",
        geo_order_whitelist_phones="",
    )
    _mock_insights(monkeypatch, _insights_response("SA"))
    e164, national = normalize_ksa_phone("0501234567")
    await check_order_geo("1.2.3.4", e164, national)


@pytest.mark.asyncio
async def test_api_error_in_production_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    from geoip2.errors import AuthenticationError

    _settings(
        monkeypatch,
        app_env="production",
        geo_check_enabled=True,
        maxmind_account_id="1",
        maxmind_license_key="bad",
        geo_order_whitelist_phones="",
    )

    async def fail_lookup(ip: str) -> object:
        raise AuthenticationError("bad credentials")

    monkeypatch.setattr("app.services.geoip._lookup_insights", fail_lookup)
    e164, national = normalize_ksa_phone("0501234567")
    with pytest.raises(GeoBlockError) as exc:
        await check_order_geo("1.2.3.4", e164, national)
    assert exc.value.reason == GEO_CHECK_FAILED


@pytest.mark.asyncio
async def test_geo_check_disabled_in_production_blocks(monkeypatch: pytest.MonkeyPatch) -> None:
    _settings(
        monkeypatch,
        app_env="production",
        geo_check_enabled=False,
        maxmind_account_id="1",
        maxmind_license_key="key",
        geo_order_whitelist_phones="",
    )
    e164, national = normalize_ksa_phone("0501234567")
    with pytest.raises(GeoBlockError) as exc:
        await check_order_geo("1.2.3.4", e164, national)
    assert exc.value.reason == GEO_CHECK_FAILED


@pytest.mark.asyncio
async def test_geo_check_disabled_in_development_skips(monkeypatch: pytest.MonkeyPatch) -> None:
    _settings(
        monkeypatch,
        app_env="development",
        geo_check_enabled=False,
        maxmind_account_id="",
        maxmind_license_key="",
        geo_order_whitelist_phones="",
    )
    e164, national = normalize_ksa_phone("0501234567")
    await check_order_geo("1.2.3.4", e164, national)
