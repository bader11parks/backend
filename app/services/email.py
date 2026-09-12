from __future__ import annotations

import asyncio
import logging
import re
import smtplib
from email.message import EmailMessage

from app.config import settings

log = logging.getLogger("mazaj.email")

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class EmailError(Exception):
    pass


def validate_email(value: str) -> str:
    email = value.strip().lower()
    if not email or len(email) > 254 or not _EMAIL_RE.match(email):
        raise EmailError("invalid_email")
    return email


def _send_sync(to: str, subject: str, body: str) -> None:
    if not settings.smtp_host or not settings.contact_email_to:
        raise EmailError("email_not_configured")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from or settings.smtp_user or settings.contact_email_to
    msg["To"] = to
    msg.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        if settings.smtp_user and settings.smtp_password:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(msg)


async def send_contact_email(name: str, email: str, message: str) -> None:
    subject = f"طلب تواصل — {name}"
    body = (
        f"اسم العميلة: {name}\n"
        f"الإيميل: {email}\n\n"
        f"الرسالة:\n{message}\n"
    )
    try:
        await asyncio.to_thread(_send_sync, settings.contact_email_to, subject, body)
    except EmailError:
        raise
    except Exception as exc:
        log.exception("contact_email_failed")
        raise EmailError("send_failed") from exc
