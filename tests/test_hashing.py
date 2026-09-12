from app.services.hashing import digits_country, meta_snap_phone_hash, tiktok_phone_hash


def test_plus_sign_difference() -> None:
    e164 = "+966501234567"
    assert digits_country(e164) == "966501234567"
    meta = meta_snap_phone_hash(e164)
    tiktok = tiktok_phone_hash(e164)
    assert meta != tiktok
    assert len(meta) == 64
    assert len(tiktok) == 64
