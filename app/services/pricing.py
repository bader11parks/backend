from __future__ import annotations

from app.catalog import OFFERS, SHIPPING_HALALAS, UPSELL_HALALAS, pick_upsell_sku, product_by_sku, promo_total_for_qty


class PricingError(ValueError):
    pass


def _allocate_promo_total(qtys: list[int], promo_total: int) -> list[int]:
    total_qty = sum(qtys)
    if total_qty == 0:
        return []
    lines: list[int] = []
    allocated = 0
    for i, qty in enumerate(qtys):
        if i == len(qtys) - 1:
            lines.append(promo_total - allocated)
        else:
            share = round(promo_total * qty / total_qty)
            lines.append(share)
            allocated += share
    return lines


def price_items(items: list[dict]) -> tuple[list[dict], int, str]:
    if not items:
        raise PricingError("empty_cart")

    validated: list[tuple[str, str, int, dict]] = []
    skus: set[str] = set()

    for item in items:
        sku = item.get("sku")
        offer_id = item.get("offer_id")
        product = product_by_sku(sku or "")
        if not product or offer_id not in OFFERS:
            raise PricingError("invalid_item")
        qty, _ = OFFERS[offer_id]
        skus.add(sku)
        validated.append((sku, offer_id, qty, product))

    total_qty = sum(v[2] for v in validated)
    promo_total = promo_total_for_qty(total_qty)
    line_totals = _allocate_promo_total([v[2] for v in validated], promo_total)

    priced: list[dict] = []
    for (sku, offer_id, qty, product), line_halalas in zip(validated, line_totals):
        priced.append(
            {
                "sku": sku,
                "offer_id": offer_id,
                "qty": qty,
                "unit_halalas": line_halalas // qty,
                "line_halalas": line_halalas,
                "name_ar": product["name_ar"],
            }
        )

    total = promo_total + SHIPPING_HALALAS
    return priced, total, pick_upsell_sku(skus)


def add_upsell(items: list[dict], sku: str) -> tuple[list[dict], int]:
    product = product_by_sku(sku)
    if not product:
        raise PricingError("invalid_upsell")
    extra = {
        "sku": sku,
        "offer_id": "upsell",
        "qty": 1,
        "unit_halalas": UPSELL_HALALAS,
        "line_halalas": UPSELL_HALALAS,
        "name_ar": product["name_ar"],
    }
    new_items = list(items) + [extra]
    total = sum(i["line_halalas"] for i in new_items) + SHIPPING_HALALAS
    return new_items, total


def halalas_to_sar(halalas: int) -> int:
    return halalas // 100
