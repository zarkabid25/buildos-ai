"""Email delivery (Phase 8, PLAT-047). Confirmed before writing this: no
SMTP/SES/SendGrid is configured anywhere in this app. Every call here is
therefore expected to record NOT_CONFIGURED -- an honest, visible status --
rather than silently pretending a message was sent. If a real provider is
ever wired in, only this one function needs to change; every caller already
treats the return value as "what actually happened," not an assumption."""

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.enums import EmailDeliveryStatus
from app.models.platform_notification import EmailDeliveryLog

settings = get_settings()


def send_email(db: Session, to_email: str, subject: str, body: str) -> EmailDeliveryLog:
    # No provider configured in this environment (see module docstring) --
    # record the honest status rather than a pretended SENT. A real
    # integration would set smtp_host/an API key in Settings and branch here.
    status_value = EmailDeliveryStatus.NOT_CONFIGURED
    error = "No email provider is configured for this environment."

    log = EmailDeliveryLog(to_email=to_email, subject=subject[:255], body=body, status=status_value, error=error)
    db.add(log)
    db.flush()
    return log
