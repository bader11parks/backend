from app.catalog import pick_upsell_sku, promo_total_for_qty
from app.services.pricing import PricingError, add_upsell, price_items


def test_promo_total_for_qty_table() -> None:
    assert promo_total_for_qty(0) == 0
    assert promo_total_for_qty(1) == 17900
    assert promo_total_for_qty(2) == 27900
    assert promo_total_for_qty(3) == 37900
    assert promo_total_for_qty(4) == 55800
    assert promo_total_for_qty(5) == 65800
    assert promo_total_for_qty(6) == 75800
    assert promo_total_for_qty(7) == 93700
    assert promo_total_for_qty(8) == 103700
    assert promo_total_for_qty(9) == 113700


def test_offer_one() -> None:
    items, total, upsell = price_items([{"sku": "MR-MATCHA", "offer_id": "one"}])
    assert total == 17900
    assert items[0]["qty"] == 1
    assert sum(i["line_halalas"] for i in items) == 17900
    assert upsell == "MR-NIGHT"


def test_offer_two_same_sku() -> None:
    items, total, _ = price_items([{"sku": "MR-MATCHA", "offer_id": "two"}])
    assert total == 27900
    assert items[0]["qty"] == 2


def test_two_different_products() -> None:
    items, total, _ = price_items(
        [
            {"sku": "MR-MATCHA", "offer_id": "one"},
            {"sku": "MR-CACAO", "offer_id": "one"},
        ]
    )
    assert total == 27900
    assert sum(i["line_halalas"] for i in items) == 27900


def test_three_different_products() -> None:
    items, total, _ = price_items(
        [
            {"sku": "MR-MATCHA", "offer_id": "one"},
            {"sku": "MR-CACAO", "offer_id": "one"},
            {"sku": "MR-NIGHT", "offer_id": "one"},
        ]
    )
    assert total == 37900
    assert sum(i["line_halalas"] for i in items) == 37900


def test_offer_three() -> None:
    _, total, _ = price_items([{"sku": "MR-NIGHT", "offer_id": "three"}])
    assert total == 37900


def test_four_products() -> None:
    items, total, _ = price_items(
        [
            {"sku": "MR-MATCHA", "offer_id": "one"},
            {"sku": "MR-CACAO", "offer_id": "one"},
            {"sku": "MR-NIGHT", "offer_id": "one"},
            {"sku": "MR-MATCHA", "offer_id": "one"},
        ]
    )
    assert total == 55800
    assert sum(i["line_halalas"] for i in items) == 55800


def test_five_products() -> None:
    _, total, _ = price_items(
        [
            {"sku": "MR-MATCHA", "offer_id": "one"},
            {"sku": "MR-CACAO", "offer_id": "one"},
            {"sku": "MR-NIGHT", "offer_id": "three"},
        ]
    )
    assert total == 65800


def test_six_products() -> None:
    _, total, _ = price_items(
        [
            {"sku": "MR-MATCHA", "offer_id": "three"},
            {"sku": "MR-CACAO", "offer_id": "three"},
        ]
    )
    assert total == 75800


def test_seven_products() -> None:
    _, total, _ = price_items(
        [
            {"sku": "MR-MATCHA", "offer_id": "three"},
            {"sku": "MR-CACAO", "offer_id": "three"},
            {"sku": "MR-NIGHT", "offer_id": "one"},
        ]
    )
    assert total == 93700


def test_eight_products() -> None:
    _, total, _ = price_items(
        [
            {"sku": "MR-MATCHA", "offer_id": "three"},
            {"sku": "MR-CACAO", "offer_id": "three"},
            {"sku": "MR-NIGHT", "offer_id": "two"},
        ]
    )
    assert total == 103700


def test_nine_products() -> None:
    _, total, _ = price_items(
        [
            {"sku": "MR-MATCHA", "offer_id": "three"},
            {"sku": "MR-CACAO", "offer_id": "three"},
            {"sku": "MR-NIGHT", "offer_id": "three"},
        ]
    )
    assert total == 113700


def test_upsell_adds_109() -> None:
    items, total, sku = price_items([{"sku": "MR-MATCHA", "offer_id": "two"}])
    new_items, new_total = add_upsell(items, sku)
    assert new_total == 27900 + 10900
    assert new_items[-1]["offer_id"] == "upsell"


def test_all_three_upsell_night() -> None:
    sku = pick_upsell_sku({"MR-MATCHA", "MR-CACAO", "MR-NIGHT"})
    assert sku == "MR-NIGHT"


def test_empty_cart() -> None:
    try:
        price_items([])
        assert False
    except PricingError:
        pass
