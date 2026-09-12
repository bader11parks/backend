"""Catalog v1 — keep identical to frontend/lib/catalog.ts."""

from __future__ import annotations

CATALOG_VERSION = 1

OFFERS: dict[str, tuple[int, int]] = {
    "one": (1, 17900),
    "two": (2, 27900),
    "three": (3, 37900),
}

UPSELL_HALALAS = 10900
SHIPPING_HALALAS = 0

CART_PROMO_TIERS: dict[int, int] = {1: 17900, 2: 27900, 3: 37900}


def promo_total_for_qty(qty: int) -> int:
    if qty <= 0:
        return 0
    groups = qty // 3
    remainder = qty % 3
    return groups * CART_PROMO_TIERS[3] + (CART_PROMO_TIERS[remainder] if remainder else 0)

PRODUCTS: list[dict] = [
    {
        "sku": "MR-MATCHA",
        "slug": "matcha-theanine",
        "name_ar": "ماتشا مع إل-ثيانين لطاقة هادئة ومتوازنة",
        "house_name": "طقس الصباح",
        "ritual_slot": "صباح",
        "kicker": "طقس الصباح",
        "heading": "طاقة هادئة من أول فنجان",
        "sub": "ماتشا مع إل-ثيانين — صحو بدون عصبية القهوة.",
        "micro_proof": "تركيبة للتركيز الهادئ",
        "active": True,
    },
    {
        "sku": "MR-CACAO",
        "slug": "cacao-ashwagandha",
        "name_ar": "كاكاو مع أشواغاندا للحظات من الهدوء وسط يومك",
        "house_name": "طقس الظهر",
        "ritual_slot": "وسط اليوم",
        "kicker": "طقس وسط اليوم",
        "heading": "هدوء له طعم دافئ",
        "sub": "كاكاو مع أشواغاندا — لحظة تنزل فيها درجة اليوم.",
        "micro_proof": "للتوتر اللي يتراكم بعد الظهر",
        "active": True,
    },
    {
        "sku": "MR-NIGHT",
        "slug": "magnesium-night",
        "name_ar": "مشروب المغنيسيوم لروتين هادئ قبل النوم",
        "house_name": "طقس الليل",
        "ritual_slot": "قبل النوم",
        "kicker": "طقس الليل",
        "heading": "هبوط ناعم قبل النوم",
        "sub": "مشروب مغنيسيوم — روتين يقفل اليوم برفق.",
        "micro_proof": "للعقل اللي يرفض ينطفي",
        "active": True,
    },
]

SKU_ORDER = ["MR-MATCHA", "MR-CACAO", "MR-NIGHT"]


def product_by_sku(sku: str) -> dict | None:
    for p in PRODUCTS:
        if p["sku"] == sku:
            return p
    return None


def pick_upsell_sku(cart_skus: set[str]) -> str:
    missing = [s for s in SKU_ORDER if s not in cart_skus]
    if not missing:
        return "MR-NIGHT"
    if "MR-MATCHA" in cart_skus and "MR-NIGHT" in missing:
        return "MR-NIGHT"
    if "MR-NIGHT" in cart_skus and "MR-MATCHA" in missing:
        return "MR-MATCHA"
    if "MR-CACAO" in cart_skus:
        if "MR-MATCHA" in missing:
            return "MR-MATCHA"
        if "MR-NIGHT" in missing:
            return "MR-NIGHT"
    return missing[0]
