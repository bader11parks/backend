from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings
from app.services.hashing import (
    country_hash,
    external_id_hash,
    meta_snap_phone_hash,
    name_hash,
    tiktok_phone_hash,
)

log = logging.getLogger("mazaj.tapi")

SNAP_EVENT_MAP = {
    "PageView": "PAGE_VIEW",
    "ViewContent": "VIEW_CONTENT",
    "AddToCart": "ADD_CART",
    "InitiateCheckout": "START_CHECKOUT",
    "Purchase": "PURCHASE",
    "Lead": "SIGN_UP",
    "Contact": "SIGN_UP",
}


def _contents(contents: list[dict] | None) -> list[dict]:
    out = []
    for c in contents or []:
        out.append(
            {
                "id": c.get("id"),
                "quantity": int(c.get("quantity") or 1),
                "item_price": float(c.get("item_price") or 0),
            }
        )
    return out


async def send_capi_event(
    *,
    event_name: str,
    event_id: str,
    event_source_url: str,
    user_agent: str,
    ip: str | None,
    value: float | None,
    contents: list[dict] | None,
    order_id: str | None = None,
    phone_e164: str | None = None,
    name: str | None = None,
    fbp: str | None = None,
    fbc: str | None = None,
    ttclid: str | None = None,
    ttp: str | None = None,
    sccid: str | None = None,
) -> None:
    async with httpx.AsyncClient(timeout=8.0) as client:
        await _maybe_meta(
            client,
            event_name=event_name,
            event_id=event_id,
            event_source_url=event_source_url,
            user_agent=user_agent,
            ip=ip,
            value=value,
            contents=contents,
            order_id=order_id,
            phone_e164=phone_e164,
            name=name,
            fbp=fbp,
            fbc=fbc,
        )
        await _maybe_tiktok(
            client,
            event_name=event_name,
            event_id=event_id,
            event_source_url=event_source_url,
            user_agent=user_agent,
            ip=ip,
            value=value,
            contents=contents,
            order_id=order_id,
            phone_e164=phone_e164,
            name=name,
            ttclid=ttclid,
            ttp=ttp,
        )
        await _maybe_snap(
            client,
            event_name=event_name,
            event_id=event_id,
            event_source_url=event_source_url,
            user_agent=user_agent,
            ip=ip,
            value=value,
            contents=contents,
            order_id=order_id,
            phone_e164=phone_e164,
            name=name,
            sccid=sccid,
        )


async def _post_once(client: httpx.AsyncClient, method: str, url: str, **kwargs: Any) -> None:
    try:
        r = await client.request(method, url, **kwargs)
        if r.status_code >= 400:
            log.warning("capi_http_error url=%s status=%s body=%s", url, r.status_code, r.text[:300])
            r = await client.request(method, url, **kwargs)
            if r.status_code >= 400:
                log.warning("capi_retry_failed url=%s status=%s", url, r.status_code)
    except Exception as exc:  # noqa: BLE001
        log.warning("capi_exception url=%s err=%s", url, exc)


async def _maybe_meta(client: httpx.AsyncClient, **kw: Any) -> None:
    if not settings.meta_pixel_id or not settings.meta_capi_access_token:
        return
    user: dict[str, Any] = {
        "client_ip_address": kw.get("ip"),
        "client_user_agent": kw.get("user_agent"),
        "country": country_hash(),
    }
    if kw.get("fbp"):
        user["fbp"] = kw["fbp"]
    if kw.get("fbc"):
        user["fbc"] = kw["fbc"]
    if kw.get("phone_e164"):
        user["ph"] = [meta_snap_phone_hash(kw["phone_e164"])]
        user["external_id"] = [external_id_hash(kw["phone_e164"])]
    if kw.get("name"):
        user["fn"] = [name_hash(kw["name"])]
    custom: dict[str, Any] = {
        "currency": "SAR",
        "content_type": "product",
    }
    if kw.get("value") is not None:
        custom["value"] = float(kw["value"])
    contents = _contents(kw.get("contents"))
    if contents:
        custom["contents"] = [
            {"id": c["id"], "quantity": c["quantity"], "item_price": c["item_price"]}
            for c in contents
        ]
        custom["content_ids"] = [c["id"] for c in contents]
        custom["num_items"] = sum(c["quantity"] for c in contents)
    if kw.get("order_id"):
        custom["order_id"] = kw["order_id"]
    payload: dict[str, Any] = {
        "data": [
            {
                "event_name": kw["event_name"],
                "event_time": __import__("time").time().__int__(),
                "event_id": kw["event_id"],
                "event_source_url": kw["event_source_url"],
                "action_source": "website",
                "user_data": {k: v for k, v in user.items() if v},
                "custom_data": custom,
            }
        ]
    }
    if settings.meta_test_event_code:
        payload["test_event_code"] = settings.meta_test_event_code
    url = f"https://graph.facebook.com/v21.0/{settings.meta_pixel_id}/events"
    await _post_once(
        client,
        "POST",
        url,
        params={"access_token": settings.meta_capi_access_token},
        json=payload,
    )


async def _maybe_tiktok(client: httpx.AsyncClient, **kw: Any) -> None:
    if not settings.tiktok_pixel_id or not settings.tiktok_access_token:
        return
    user: dict[str, Any] = {}
    if kw.get("phone_e164"):
        user["phone"] = tiktok_phone_hash(kw["phone_e164"])
        user["external_id"] = external_id_hash(kw["phone_e164"])
    properties: dict[str, Any] = {
        "currency": "SAR",
        "content_type": "product",
    }
    if kw.get("value") is not None:
        properties["value"] = float(kw["value"])
    contents = _contents(kw.get("contents"))
    if contents:
        properties["contents"] = [
            {"content_id": c["id"], "quantity": c["quantity"], "price": c["item_price"]}
            for c in contents
        ]
        properties["content_ids"] = [c["id"] for c in contents]
    if kw.get("order_id"):
        properties["order_id"] = kw["order_id"]
    context: dict[str, Any] = {
        "user_agent": kw.get("user_agent"),
        "ip": kw.get("ip"),
        "page": {"url": kw.get("event_source_url")},
    }
    if kw.get("ttclid") or kw.get("ttp"):
        ad: dict[str, Any] = {}
        if kw.get("ttclid"):
            ad["callback"] = kw["ttclid"]
        context["ad"] = ad
        if kw.get("ttp"):
            user["ttp"] = kw["ttp"]
    event: dict[str, Any] = {
        "event": kw["event_name"],
        "event_id": kw["event_id"],
        "event_time": __import__("time").time().__int__(),
        "user": user,
        "properties": properties,
        "page": {"url": kw.get("event_source_url")},
        "context": context,
    }
    payload: dict[str, Any] = {
        "event_source": "web",
        "event_source_id": settings.tiktok_pixel_id,
        "data": [event],
    }
    if settings.tiktok_test_event_code:
        payload["test_event_code"] = settings.tiktok_test_event_code
    await _post_once(
        client,
        "POST",
        "https://business-api.tiktok.com/open_api/v1.3/event/track/",
        headers={"Access-Token": settings.tiktok_access_token, "Content-Type": "application/json"},
        json=payload,
    )


async def _maybe_snap(client: httpx.AsyncClient, **kw: Any) -> None:
    if not settings.snap_pixel_id or not settings.snap_capi_token:
        return
    snap_name = SNAP_EVENT_MAP.get(kw["event_name"], kw["event_name"])
    user: dict[str, Any] = {
        "client_ip_address": kw.get("ip"),
        "client_user_agent": kw.get("user_agent"),
        "country": country_hash(),
    }
    if kw.get("phone_e164"):
        user["ph"] = [meta_snap_phone_hash(kw["phone_e164"])]
        user["external_id"] = [external_id_hash(kw["phone_e164"])]
    if kw.get("sccid"):
        user["sc_click_id"] = kw["sccid"]
    custom: dict[str, Any] = {"currency": "SAR", "content_type": "product"}
    if kw.get("value") is not None:
        custom["value"] = float(kw["value"])
    contents = _contents(kw.get("contents"))
    if contents:
        custom["content_ids"] = [c["id"] for c in contents]
        custom["num_items"] = sum(c["quantity"] for c in contents)
    if kw.get("order_id"):
        custom["order_id"] = kw["order_id"]
        custom["transaction_id"] = kw["order_id"]
    payload = {
        "data": [
            {
                "event_name": snap_name,
                "event_time": __import__("time").time().__int__(),
                "event_id": kw["event_id"],
                "event_source_url": kw["event_source_url"],
                "action_source": "WEB",
                "user_data": {k: v for k, v in user.items() if v},
                "custom_data": custom,
            }
        ]
    }
    url = f"https://tr.snapchat.com/v3/{settings.snap_pixel_id}/events"
    await _post_once(
        client,
        "POST",
        url,
        params={"access_token": settings.snap_capi_token},
        json=payload,
    )
