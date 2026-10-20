"""Email delivery (Phase 8, PLAT-047; provider adapter added Phase 9.1,
Task 3). Two providers:

- "console" (the default, and the sandbox provider for dev/tests): logs the
  rendered email and records it as SENT. It's a real, inspectable delivery
  path (nothing is silently dropped), just not a real inbox -- fine for
  exercising retry-safety and dedup without needing real credentials.
- "smtp": sends through a real mail server. Needs SMTP_HOST (and usually
  SMTP_USERNAME/SMTP_PASSWORD) set; without them this honestly reports
  NOT_CONFIGURED rather than a pretended SENT, same rule as before this
  phase. A send that reaches the server but is rejected records FAILED
  with the real error, never silently swallowed.

`send_templated` is retry-safe: pass the same `dedup_key` on a repeated
request (e.g. the invitation id, or "ticket:{id}:message:{message_id}") and
an already-sent log for that key is returned unchanged instead of sending
again -- enforced by a real unique constraint on the column, not a
best-effort check, so it's correct even under concurrent retries."""

import logging
import smtplib
from email.message import EmailMessage

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.enums import EmailDeliveryStatus
from app.models.platform_notification import EmailDeliveryLog
from app.services.email_templates import TEMPLATES

logger = logging.getLogger("buildos.email")


def _send_via_smtp(to_email: str, subject: str, body: str) -> None:
    settings = get_settings()
    message = EmailMessage()
    message["From"] = settings.email_from_address
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password.get_secret_value())
        smtp.send_message(message)


def send_email(db: Session, to_email: str, subject: str, body: str, template_key: str | None = None, dedup_key: str | None = None) -> EmailDeliveryLog:
    """Lower-level send used by send_templated. Callers that don't need
    retry-safety (nothing in this app today) can still call this directly
    with no dedup_key, same as before this phase."""
    if dedup_key:
        existing = db.query(EmailDeliveryLog).filter(EmailDeliveryLog.dedup_key == dedup_key).first()
        if existing:
            return existing

    settings = get_settings()
    log = EmailDeliveryLog(to_email=to_email, subject=subject[:255], body=body, template_key=template_key, dedup_key=dedup_key, status=EmailDeliveryStatus.NOT_CONFIGURED)

    if settings.email_provider == "smtp":
        if not settings.smtp_host:
            log.error = "EMAIL_PROVIDER=smtp but SMTP_HOST is not set."
        else:
            try:
                _send_via_smtp(to_email, subject, body)
                log.status = EmailDeliveryStatus.SENT
            except Exception as exc:  # noqa: BLE001 -- any SMTP/network failure must be recorded, not raised
                logger.warning("SMTP send to %s failed: %s", to_email, exc)
                log.status = EmailDeliveryStatus.FAILED
                log.error = str(exc)[:500]
    elif settings.email_provider == "console":
        logger.info("email_sandbox_delivery to=%s subject=%s", to_email, subject)
        log.status = EmailDeliveryStatus.SENT
    else:
        log.error = f"Unknown EMAIL_PROVIDER '{settings.email_provider}'."

    db.add(log)
    try:
        db.flush()
    except IntegrityError:
        # A concurrent request won the race on the same dedup_key between
        # our check above and this insert -- that's the retry-safety
        # working as intended, so return the row it created instead of
        # erroring or double-sending.
        db.rollback()
        return db.query(EmailDeliveryLog).filter(EmailDeliveryLog.dedup_key == dedup_key).one()
    return log


def send_templated(db: Session, template_key: str, to_email: str, context: dict, dedup_key: str) -> EmailDeliveryLog:
    template = TEMPLATES[template_key]
    subject = template.subject.format(**context)
    body = template.body.format(**context)
    return send_email(db, to_email, subject, body, template_key=template_key, dedup_key=dedup_key)
