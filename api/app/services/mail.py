import asyncio
import html
import ssl
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path
from typing import Literal

import aiosmtplib

from app.config import settings

MailKind = Literal["auth", "notification"]

_OTP_HTML_TEMPLATE = (Path(__file__).with_name("otp_email.html")).read_text(encoding="utf-8")
OTP_EMAIL_SUBJECT = "Код для входа на Iter.Factiosi"


def _from_header(kind: MailKind) -> str:
    name = (
        settings.smtp_from_display_auth
        if kind == "auth"
        else settings.smtp_from_display_notification
    )
    return formataddr((name, settings.smtp_from))


async def send_plain_email(
    to_addr: str,
    subject: str,
    body: str,
    *,
    kind: MailKind = "notification",
) -> None:
    """Отправка простого текстового письма (уведомления и т.п.)."""
    if not settings.smtp_user or not settings.smtp_password:
        raise RuntimeError("SMTP is not configured")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = _from_header(kind)
    msg["To"] = to_addr
    msg.set_content(body)

    use_tls = settings.smtp_use_tls
    tls_context = ssl.create_default_context() if use_tls else None

    await asyncio.wait_for(
        aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            use_tls=use_tls,
            tls_context=tls_context,
            timeout=25,
        ),
        timeout=35.0,
    )


async def _send_message(msg: EmailMessage) -> None:
    use_tls = settings.smtp_use_tls
    tls_context = ssl.create_default_context() if use_tls else None
    await asyncio.wait_for(
        aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            use_tls=use_tls,
            tls_context=tls_context,
            timeout=25,
        ),
        timeout=35.0,
    )


async def send_otp_email(to_addr: str, code: str) -> None:
    if not settings.smtp_user or not settings.smtp_password:
        raise RuntimeError("SMTP is not configured")

    safe_code = html.escape(code, quote=True)
    html_body = _OTP_HTML_TEMPLATE.replace("{{CODE}}", safe_code)
    plain = (
        f"{OTP_EMAIL_SUBJECT}\n\n"
        f"Ваш код: {code}\n\n"
        "Код действителен в течение 10 минут и может быть использован только один раз.\n\n"
        "Если вы не запрашивали этот код — проигнорируйте письмо.\n"
        "Никогда не делитесь этим кодом с другими людьми.\n"
    )

    msg = EmailMessage()
    msg["Subject"] = OTP_EMAIL_SUBJECT
    msg["From"] = _from_header("auth")
    msg["To"] = to_addr
    msg.set_content(plain)
    msg.add_alternative(html_body, subtype="html")

    await _send_message(msg)


def send_otp_email_sync(to_addr: str, code: str) -> None:
    asyncio.run(send_otp_email(to_addr, code))
