import pytest

from app.services.phone import PhoneError, normalize_ksa_phone, validate_name


def test_05_format() -> None:
    e164, national = normalize_ksa_phone("0501234567")
    assert e164 == "+966501234567"
    assert national == "0501234567"


def test_5_format() -> None:
    e164, _ = normalize_ksa_phone("501234567")
    assert e164 == "+966501234567"


def test_plus() -> None:
    e164, _ = normalize_ksa_phone("+966501234567")
    assert e164 == "+966501234567"


def test_966() -> None:
    e164, _ = normalize_ksa_phone("966501234567")
    assert e164 == "+966501234567"


def test_reject_uae() -> None:
    with pytest.raises(PhoneError):
        normalize_ksa_phone("+971501234567")


def test_reject_landline_like() -> None:
    with pytest.raises(PhoneError):
        normalize_ksa_phone("0112345678")


def test_name_ok() -> None:
    assert validate_name("نورة") == "نورة"


def test_name_too_short() -> None:
    with pytest.raises(PhoneError):
        validate_name("ن")
