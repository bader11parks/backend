from __future__ import annotations

import re

import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberType


class PhoneError(ValueError):
    pass


_ARABIC_OR_LATIN = re.compile(r"^[\u0600-\u06FFa-zA-Z\s'.-]{2,40}$")


def validate_name(name: str) -> str:
    cleaned = " ".join(name.strip().split())
    if not _ARABIC_OR_LATIN.match(cleaned):
        raise PhoneError("invalid_name")
    return cleaned


def normalize_ksa_phone(raw: str) -> tuple[str, str]:
    """Return (e164, national like 05xxxxxxxx)."""
    digits = re.sub(r"[^\d+]", "", raw.strip())
    if digits.startswith("00966"):
        digits = "+" + digits[2:]
    elif digits.startswith("966") and not digits.startswith("+"):
        digits = "+" + digits
    elif digits.startswith("05") and len(digits) == 10:
        digits = "+966" + digits[1:]
    elif digits.startswith("5") and len(digits) == 9:
        digits = "+966" + digits
    elif digits.startswith("+966"):
        pass
    else:
        raise PhoneError("invalid_phone")

    try:
        parsed = phonenumbers.parse(digits, "SA")
    except NumberParseException as exc:
        raise PhoneError("invalid_phone") from exc

    if parsed.country_code != 966:
        raise PhoneError("invalid_phone")

    national = str(parsed.national_number)
    if not (national.startswith("5") and len(national) == 9):
        raise PhoneError("invalid_phone")
    if not phonenumbers.is_possible_number(parsed):
        raise PhoneError("invalid_phone")
    if phonenumbers.is_valid_number(parsed):
        ntype = phonenumbers.number_type(parsed)
        if ntype == PhoneNumberType.FIXED_LINE:
            raise PhoneError("invalid_phone")

    e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    national_n = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL)
    national_digits = re.sub(r"\D", "", national_n)
    if not national_digits.startswith("05"):
        national_digits = "0" + str(parsed.national_number)
    return e164, national_digits


def mask_phone_national(national: str) -> str:
    if len(national) < 8:
        return "05****"
    return national[:2] + "****" + national[-4:]
