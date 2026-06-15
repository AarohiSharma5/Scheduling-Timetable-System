"""Lightweight transactional email sending (stdlib SMTP, no extra deps).

Configured entirely through environment variables so it works with any provider
(Resend, Brevo/Sendinblue, SendGrid, Mailgun, Gmail app-password, ...):

    SMTP_HOST       smtp.resend.com
    SMTP_PORT       587               (default 587; STARTTLS)
    SMTP_USERNAME   <provider user>
    SMTP_PASSWORD   <provider key/password>
    EMAIL_FROM      "School App <noreply@yourschool.com>"
    APP_BASE_URL    https://yourschool.onrender.com   (to build clickable links)

If SMTP is NOT configured, emails are logged to the server console instead of
sent. That keeps local dev and the very first pilot working with zero setup —
the operator can read the link from the logs — while a one-line env change in
production turns real delivery on. Sending never raises: a mail failure must not
break the API request that triggered it.
"""

import os
import smtplib
import logging
from email.message import EmailMessage

logger = logging.getLogger("email")


def is_configured() -> bool:
    return bool(os.getenv("SMTP_HOST") and os.getenv("EMAIL_FROM"))


def app_base_url() -> str:
    """Public base URL for building absolute links (no trailing slash)."""
    return (os.getenv("APP_BASE_URL") or "").rstrip("/")


def absolute_url(path: str) -> str:
    """Turn an in-app path like '/accept-invite/abc' into a clickable URL."""
    base = app_base_url()
    if not path.startswith("/"):
        path = "/" + path
    return f"{base}{path}" if base else path


def send_email(to: str, subject: str, body_text: str, body_html: str | None = None) -> bool:
    """Send an email. Returns True if actually sent, False if only logged.

    Catches and logs all errors so callers can treat email as best-effort.
    """
    sender = os.getenv("EMAIL_FROM", "noreply@example.com")

    if not is_configured():
        logger.warning(
            "[email:not-configured] would send to=%s subject=%s\n%s",
            to, subject, body_text,
        )
        return False

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body_text)
    if body_html:
        msg.add_alternative(body_html, subtype="html")

    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    use_ssl = os.getenv("SMTP_USE_SSL", "0") == "1"  # port 465 style

    try:
        if use_ssl:
            server = smtplib.SMTP_SSL(host, port, timeout=15)
        else:
            server = smtplib.SMTP(host, port, timeout=15)
        with server:
            if not use_ssl:
                server.starttls()
            if username and password:
                server.login(username, password)
            server.send_message(msg)
        logger.info("[email:sent] to=%s subject=%s", to, subject)
        return True
    except Exception as exc:  # noqa: BLE001 - email must never break the request
        logger.error("[email:failed] to=%s subject=%s error=%s", to, subject, exc)
        return False


def send_invitation_email(to: str, name: str | None, role: str,
                          org_name: str | None, link_path: str) -> bool:
    """Email a new user their invitation link."""
    url = absolute_url(link_path)
    who = name or "there"
    school = org_name or "your school"
    role_label = role.replace("_", " ")
    subject = f"You've been invited to {school}"
    text = (
        f"Hi {who},\n\n"
        f"You've been invited to join {school} as a {role_label}.\n\n"
        f"Set up your account here:\n{url}\n\n"
        f"This link expires in 7 days.\n\n"
        f"If you weren't expecting this, you can ignore this email."
    )
    html = (
        f"<p>Hi {who},</p>"
        f"<p>You've been invited to join <strong>{school}</strong> as a {role_label}.</p>"
        f'<p><a href="{url}">Set up your account</a></p>'
        f"<p>This link expires in 7 days. If you weren't expecting this, ignore this email.</p>"
    )
    return send_email(to, subject, text, html)


def send_password_reset_email(to: str, name: str | None,
                              org_name: str | None, link_path: str) -> bool:
    """Email a user their password-reset link."""
    url = absolute_url(link_path)
    who = name or "there"
    school = org_name or "your school"
    subject = f"Reset your {school} password"
    text = (
        f"Hi {who},\n\n"
        f"We received a request to reset your {school} password.\n\n"
        f"Reset it here:\n{url}\n\n"
        f"This link expires in 24 hours. If you didn't request this, ignore this email."
    )
    html = (
        f"<p>Hi {who},</p>"
        f"<p>We received a request to reset your <strong>{school}</strong> password.</p>"
        f'<p><a href="{url}">Reset your password</a></p>'
        f"<p>This link expires in 24 hours. If you didn't request this, ignore this email.</p>"
    )
    return send_email(to, subject, text, html)
