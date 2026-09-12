from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.catalog import CATALOG_VERSION, OFFERS, PRODUCTS, UPSELL_HALALAS, product_by_sku
from app.db import get_session
from app.models import EmailLead, Lead, Order, OrderItem
from app.schemas import DraftOrderIn, EmailLeadIn, FinalizeIn, LeadIn, TrackIn
from app.services.email import EmailError, send_contact_email, validate_email
from app.services.capi import send_capi_event
from app.services.geoip import GEO_CHECK_FAILED, GeoBlockError, check_order_geo
from app.services.phone import PhoneError, mask_phone_national, normalize_ksa_phone, validate_name
from app.services.pricing import PricingError, add_upsell, halalas_to_sar, price_items
from app.services.sheets import post_sheet

log = logging.getLogger("mazaj.api")
router = APIRouter()

_rate: dict[str, deque[float]] = defaultdict(deque)


def client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for") or ""
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else ""


def rate_limit_draft(ip: str) -> None:
    now = time.time()
    q = _rate[ip]
    while q and now - q[0] > 3600:
        q.popleft()
    if len(q) >= 60:
        raise HTTPException(429, "rate_limited")
    q.append(now)


def _log_phone(e164: str) -> str:
    return e164[-4:] if e164 else ""


def _raise_geo_error(exc: GeoBlockError) -> None:
    if exc.reason == GEO_CHECK_FAILED:
        raise HTTPException(503, exc.reason)
    raise HTTPException(403, exc.reason)


def public_order(order: Order) -> dict:
    return {
        "order_id": str(order.id),
        "status": order.status,
        "total_sar": halalas_to_sar(order.total_halalas),
        "customer_name": order.customer_name,
        "phone_masked": mask_phone_national(order.phone_national),
        "items": [
            {
                "sku": i.sku,
                "offer_id": i.offer_id,
                "qty": i.qty,
                "name_ar": i.name_ar,
                "line_sar": i.line_halalas / 100,
            }
            for i in order.items
        ],
        "thank_you_path": f"/thank-you?order={order.id}",
        "upsell_accepted": order.upsell_accepted,
    }


@router.get("/health")
async def health(session: AsyncSession = Depends(get_session)) -> dict:
    db_ok = True
    try:
        await session.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        db_ok = False
    return {"status": "ok" if db_ok else "degraded", "db": db_ok}


@router.get("/catalog")
async def catalog() -> dict:
    return {
        "catalog_version": CATALOG_VERSION,
        "products": PRODUCTS,
        "offers": {k: {"qty": v[0], "halalas": v[1], "sar": v[1] // 100} for k, v in OFFERS.items()},
        "upsell_sar": UPSELL_HALALAS // 100,
    }


@router.post("/track")
async def track(payload: TrackIn, request: Request) -> dict:
    phone = payload.user.phone or None
    e164 = None
    if phone:
        try:
            e164, _ = normalize_ksa_phone(phone)
        except PhoneError:
            e164 = None
    await send_capi_event(
        event_name=payload.event_name,
        event_id=payload.event_id,
        event_source_url=payload.event_source_url,
        user_agent=request.headers.get("user-agent", ""),
        ip=client_ip(request),
        value=payload.value,
        contents=[c.model_dump() for c in payload.contents],
        phone_e164=e164,
        name=payload.user.name or None,
        fbp=payload.user.fbp or None,
        fbc=payload.user.fbc or None,
        ttclid=payload.user.ttclid or None,
        ttp=payload.user.ttp or None,
        sccid=payload.user.sccid or None,
    )
    return {"ok": True}


@router.post("/leads")
async def leads(payload: LeadIn, session: AsyncSession = Depends(get_session)) -> dict:
    try:
        name = validate_name(payload.name)
        e164, national = normalize_ksa_phone(payload.phone)
    except PhoneError:
        raise HTTPException(422, "invalid_contact")
    lead = Lead(name=name, phone=e164, message=payload.message.strip()[:2000])
    session.add(lead)
    await session.commit()
    return {"ok": True}


@router.post("/leads/email")
async def email_leads(payload: EmailLeadIn, session: AsyncSession = Depends(get_session)) -> dict:
    try:
        name = validate_name(payload.name)
        email = validate_email(payload.email)
    except PhoneError:
        raise HTTPException(422, "invalid_name")
    except EmailError:
        raise HTTPException(422, "invalid_email")
    message = payload.message.strip()[:2000]
    if len(message) < 3:
        raise HTTPException(422, "invalid_message")
    try:
        await send_contact_email(name, email, message)
    except EmailError as exc:
        if str(exc) == "email_not_configured":
            raise HTTPException(503, "email_not_configured")
        raise HTTPException(502, "email_send_failed")
    lead = EmailLead(name=name, email=email, message=message)
    session.add(lead)
    await session.commit()
    return {"ok": True}


@router.post("/orders/draft")
async def draft_order(
    payload: DraftOrderIn,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    ip = client_ip(request)
    rate_limit_draft(ip or "unknown")
    try:
        name = validate_name(payload.customer_name)
        e164, national = normalize_ksa_phone(payload.phone)
    except PhoneError:
        raise HTTPException(422, "invalid_phone")
    try:
        await check_order_geo(ip or "", e164, national)
    except GeoBlockError as exc:
        _raise_geo_error(exc)
    try:
        priced, total, upsell_sku = price_items([i.model_dump() for i in payload.items])
    except PricingError as exc:
        raise HTTPException(400, str(exc))

    order = Order(
        id=uuid.uuid4(),
        status="draft",
        customer_name=name,
        phone_e164=e164,
        phone_national=national,
        total_halalas=total,
        shipping_halalas=0,
        suggested_upsell_sku=upsell_sku,
        landing_page=payload.landing_page or payload.event_source_url,
        event_id_initiate=payload.event_id_initiate or None,
        fbp=payload.fbp or None,
        fbc=payload.fbc or None,
        ttclid=payload.ttclid or None,
        ttp=payload.ttp or None,
        sccid=payload.sccid or None,
        utm_source=payload.utm.source or None,
        utm_medium=payload.utm.medium or None,
        utm_campaign=payload.utm.campaign or None,
        utm_content=payload.utm.content or None,
        utm_term=payload.utm.term or None,
        ip=ip or None,
        user_agent=payload.user_agent or request.headers.get("user-agent"),
    )
    for row in priced:
        order.items.append(OrderItem(**row))
    session.add(order)
    await session.commit()
    await session.refresh(order)
    upsell_product = product_by_sku(upsell_sku)
    log.info("draft_created order=%s phone=***%s", order.id, _log_phone(e164))
    return {
        "order_id": str(order.id),
        "status": "draft",
        "total_sar": halalas_to_sar(total),
        "upsell": {
            "sku": upsell_sku,
            "name_ar": upsell_product["name_ar"] if upsell_product else "",
            "price_sar": 109,
        },
        "expires_in": 12,
    }


async def _do_finalize(
    order_id: uuid.UUID,
    accept_upsell: bool,
    event_id_purchase: str,
    session: AsyncSession,
    request: Request,
) -> dict:
    result = await session.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(404, "not_found")

    if order.status != "draft" and order.purchase_sent_at:
        return public_order(order)
    if order.status == "pending_cod" and order.purchase_sent_at:
        return public_order(order)

    if order.status == "draft":
        try:
            await check_order_geo(
                order.ip or client_ip(request) or "",
                order.phone_e164,
                order.phone_national,
            )
        except GeoBlockError as exc:
            _raise_geo_error(exc)
        items_dicts = [
            {
                "sku": i.sku,
                "offer_id": i.offer_id,
                "qty": i.qty,
                "unit_halalas": i.unit_halalas,
                "line_halalas": i.line_halalas,
                "name_ar": i.name_ar,
            }
            for i in order.items
        ]
        if accept_upsell and order.suggested_upsell_sku:
            already = any(i.offer_id == "upsell" for i in order.items)
            if not already:
                new_items, total = add_upsell(items_dicts, order.suggested_upsell_sku)
                extra = new_items[-1]
                session.add(OrderItem(order_id=order.id, **extra))
                order.total_halalas = total
                order.upsell_accepted = True
                order.upsell_sku = order.suggested_upsell_sku
        order.status = "pending_cod"
        order.event_id_purchase = event_id_purchase
        await session.commit()
        await session.refresh(order)
        result = await session.execute(
            select(Order).options(selectinload(Order.items)).where(Order.id == order.id)
        )
        order = result.scalar_one()

    contents = [
        {
            "id": i.sku,
            "quantity": i.qty,
            "item_price": (i.line_halalas / 100) / max(i.qty, 1),
        }
        for i in order.items
    ]
    if not order.purchase_sent_at:
        try:
            await send_capi_event(
                event_name="Purchase",
                event_id=order.event_id_purchase or event_id_purchase,
                event_source_url=order.landing_page or "https://mazajrituals.shop",
                user_agent=order.user_agent or request.headers.get("user-agent", ""),
                ip=order.ip or client_ip(request),
                value=float(halalas_to_sar(order.total_halalas)),
                contents=contents,
                order_id=str(order.id),
                phone_e164=order.phone_e164,
                name=order.customer_name,
                fbp=order.fbp,
                fbc=order.fbc,
                ttclid=order.ttclid,
                ttp=order.ttp,
                sccid=order.sccid,
            )
            order.purchase_sent_at = datetime.now(timezone.utc)
        except Exception as exc:  # noqa: BLE001
            log.warning("purchase_capi_failed order=%s err=%s", order.id, exc)
        if not order.sheet_sent_at:
            ok = await post_sheet(order)
            if ok:
                order.sheet_sent_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(order)
        result = await session.execute(
            select(Order).options(selectinload(Order.items)).where(Order.id == order.id)
        )
        order = result.scalar_one()

    return public_order(order)


@router.post("/orders/{order_id}/finalize")
async def finalize_order(
    order_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    import json

    accept = False
    event_id = str(uuid.uuid4())
    qp = request.query_params
    if "accept_upsell" in qp:
        accept = qp.get("accept_upsell", "false").lower() in ("1", "true", "yes")
    if qp.get("event_id_purchase"):
        event_id = qp["event_id_purchase"]
    raw = await request.body()
    if raw:
        try:
            parsed = FinalizeIn.model_validate(json.loads(raw.decode("utf-8")))
            accept = parsed.accept_upsell
            event_id = parsed.event_id_purchase
        except Exception:
            pass
    return await _do_finalize(order_id, accept, event_id, session, request)


@router.get("/orders/{order_id}/public")
async def public_order_get(
    order_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(404, "not_found")
    return public_order(order)
