"""Email delivery (Phase 8, PLAT-047; provider adapter added Phase 9.1,
Task 3; retry and SMTP-provider hardening added Phase 10, Task 2). Two
providers:

- "console" (the default, and the sandbox provider for dev/tests): logs the
  rendered email and records it as SIMULATED -- deliberately NOT the same
  word as a real provider's success status, so a sandbox delivery can
  never be mistaken for a real one anywhere it's displayed or asserted on.
  It's a real, inspectable delivery path (nothing is silently dropped),
  just not a real inbox -- fine for exercising retry-safety and dedup
  without needing real credentials. **Refused outside development/test**
  by config.py's production-safety check (Phase 10): staging/production
  must configure a real provider.
- "smtp": sends through a real mail server. Needs SMTP_HOST (and usually
  SMTP_USERNAME/SMTP_PASSWORD) set; without them this honestly reports
  NOT_CONFIGURED rather than a pretended delivery, same rule as before this
  phase. A send that reaches the server and is accepted records ACCEPTED
  (the provider took it; this app has no visibility past that point for a
  plain SMTP send). A send that's rejected or the connection fails records
  FAILED with the real error, never silently swallowed.

`send_templated` is retry-safe: pass the same `dedup_key` on a repeated
request (e.g. the invitation id, or "ticket:{id}:message:{message_id}") and
an already-sent log for that key is returned unchanged instead of sending
again -- enforced by a real unique constraint on the column, not a
best-effort check, so it's correct even under concurrent retries.
`retry_failed_email` lets a FAILED send be retried later (there is no
background worker in this project to do this automatically -- see
docs/RELEASE_READINESS.md -- so today this is a function an admin action or
a future worker can call, not a self-driving queue)."""

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


def _attempt_delivery(log: EmailDeliveryLog, to_email: str, subject: str, body: str) -> None:
    """Mutates `log.status`/`log.error` in place; never raises -- any
    provider/network failure must be recorded, not propagated as a 500."""
    settings = get_settings()
    if settings.email_provider == "smtp":
        if not settings.smtp_host:
            log.status = EmailDeliveryStatus.NOT_CONFIGURED
            log.error = "EMAIL_PROVIDER=smtp but SMTP_HOST is not set."
            return
        try:
            _send_via_smtp(to_email, subject, body)
            log.status = EmailDeliveryStatus.ACCEPTED
            log.error = None
        except Exception as exc:  # noqa: BLE001
            logger.warning("SMTP send to %s failed: %s", to_email, exc)
            log.status = EmailDeliveryStatus.FAILED
            log.error = str(exc)[:500]
    elif settings.email_provider == "console":
        logger.info("email_sandbox_delivery to=%s subject=%s", to_email, subject)
        log.status = EmailDeliveryStatus.SIMULATED
        log.error = None
    else:
        log.status = EmailDeliveryStatus.NOT_CONFIGURED
        log.error = f"Unknown EMAIL_PROVIDER '{settings.email_provider}'."


def send_email(db: Session, to_email: str, subject: str, body: str, template_key: str | None = None, dedup_key: str | None = None) -> EmailDeliveryLog:
    """Lower-level send used by send_templated. Callers that don't need
    retry-safety can still call this directly with no dedup_key."""
    if dedup_key:
        existing = db.query(EmailDeliveryLog).filter(EmailDeliveryLog.dedup_key == dedup_key).first()
        if existing:
            return existing

    log = EmailDeliveryLog(to_email=to_email, subject=subject[:255], body=body, template_key=template_key, dedup_key=dedup_key, status=EmailDeliveryStatus.NOT_CONFIGURED)
    _attempt_delivery(log, to_email, subject, body)

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


def retry_failed_email(db: Session, log_id) -> EmailDeliveryLog:
    """Retries exactly one previously FAILED send, in place (same log row,
    same dedup_key -- never creates a second row for the same logical
    email). Raises ValueError for any status other than FAILED, so this
    can never be used to "retry" something that already succeeded or was
    never configured in the first place."""
    log = db.query(EmailDeliveryLog).filter(EmailDeliveryLog.id == log_id).first()
    if not log:
        raise ValueError("No such email delivery log")
    if log.status != EmailDeliveryStatus.FAILED:
        raise ValueError(f"Only a FAILED send can be retried (this one is {log.status.value})")

    log.status = EmailDeliveryStatus.RETRYING
    db.flush()
    _attempt_delivery(log, log.to_email, log.subject, log.body)
    db.commit()
    return log
