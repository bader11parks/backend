from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from app.config import settings
from app.models import Order

log = logging.getLogger("mazaj.sheets")
RIYADH = ZoneInfo("Asia/Riyadh")


def _mask_log_phone(e164: str) -> str:
    return e164[-4:] if e164 else ""


def order_to_sheet_payload(order: Order) -> dict[str, Any]:
    created = order.created_at or datetime.now(timezone.utc)
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    riyadh = created.astimezone(RIYADH)
    items = order.items or []
    summary_parts = []
    items_json = []
    subtotal = 0
    upsell_sar = 0
    for it in items:
        line_sar = it.line_halalas / 100
        if it.offer_id == "upsell":
            upsell_sar += line_sar
        else:
            subtotal += line_sar
        summary_parts.append(f"{it.name_ar} ({it.offer_id}×{it.qty})")
        items_json.append(
            {
                "sku": it.sku,
                "offer_id": it.offer_id,
                "qty": it.qty,
                "line_sar": line_sar,
            }
        )
    return {
        "order_id": str(order.id),
        "created_at_utc": created.isoformat(),
        "created_at_riyadh": riyadh.strftime("%Y-%m-%d %H:%M:%S"),
        "status": order.status,
        "customer_name": order.customer_name,
        "phone_e164": order.phone_e164,
        "phone_national": order.phone_national,
        "payment_method": order.payment,
        "currency": order.currency,
        "subtotal_sar": subtotal,
        "upsell_sar": upsell_sar,
        "shipping_sar": order.shipping_halalas / 100,
        "total_sar": order.total_halalas / 100,
        "upsell_accepted": order.upsell_accepted,
        "upsell_sku": order.upsell_sku or "",
        "items_summary": " + ".join(summary_parts),
        "items_json": json.dumps(items_json, ensure_ascii=False),
        "landing_page": order.landing_page or "",
        "event_id_purchase": order.event_id_purchase or "",
        "utm_source": order.utm_source or "",
        "utm_medium": order.utm_medium or "",
        "utm_campaign": order.utm_campaign or "",
        "utm_content": order.utm_content or "",
        "utm_term": order.utm_term or "",
        "fbclid": "",
        "ttclid": order.ttclid or "",
        "sccid": order.sccid or "",
        "fbp": order.fbp or "",
        "fbc": order.fbc or "",
        "ip": order.ip or "",
        "user_agent": order.user_agent or "",
        "catalog_version": settings.catalog_version,
        "notes": "",
    }


async def post_sheet(order: Order) -> bool:
    if not settings.sheet_webhook_url:
        log.info("sheet_skipped_no_url order=%s phone=***%s", order.id, _mask_log_phone(order.phone_e164))
        return False
    payload = order_to_sheet_payload(order)
    headers = {"Content-Type": "application/json"}
    if settings.sheet_webhook_secret:
        headers["X-Webhook-Secret"] = settings.sheet_webhook_secret
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            r = await client.post(settings.sheet_webhook_url, json=payload, headers=headers)
            if r.status_code >= 400:
                log.warning("sheet_fail status=%s order=%s", r.status_code, order.id)
                r = await client.post(settings.sheet_webhook_url, json=payload, headers=headers)
            if r.status_code < 400:
                return True
        except Exception as exc:  # noqa: BLE001
            log.warning("sheet_exception order=%s err=%s", order.id, exc)
    return False
