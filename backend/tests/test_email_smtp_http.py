"""Phase 10 (Task 2): provider-integration tests for EMAIL_PROVIDER=smtp,
against a real SMTP server running in this process (aiosmtpd) -- not a
mocked function, not a real third-party mail provider. This exercises the
actual smtplib dial-out/EHLO/MAIL FROM/DATA conversation in
email_service._send_via_smtp, the same code a real production SMTP
provider would be driven through."""

import asyncio
import threading

import pytest
from aiosmtpd.controller import Controller
from aiosmtpd.handlers import Message as MessageHandler

from app.core.config import get_settings
from app.models.enums import EmailDeliveryStatus
from app.services import email_service


class _CapturingHandler(MessageHandler):
    def __init__(self) -> None:
        super().__init__()
        self.messages = []

    def handle_message(self, message) -> None:
        self.messages.append(message)


def _free_port() -> int:
    import socket as _socket

    with _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def smtp_server():
    handler = _CapturingHandler()
    # aiosmtpd's own startup handshake doesn't reliably support an
    # ephemeral port=0 on Windows -- pick a free one ourselves instead.
    controller = Controller(handler, hostname="127.0.0.1", port=_free_port())
    controller.start()
    try:
        yield controller, handler
    finally:
        controller.stop()


@pytest.fixture
def smtp_settings(smtp_server, monkeypatch):
    controller, _handler = smtp_server
    settings = get_settings()
    monkeypatch.setattr(settings, "email_provider", "smtp")
    monkeypatch.setattr(settings, "smtp_host", controller.hostname)
    monkeypatch.setattr(settings, "smtp_port", controller.port)
    monkeypatch.setattr(settings, "smtp_use_tls", False)
    monkeypatch.setattr(settings, "smtp_username", "")
    return settings


def test_smtp_send_is_accepted_by_a_real_smtp_server(client, smtp_server, smtp_settings):
    from app.db.session import SessionLocal

    _controller, handler = smtp_server
    db = SessionLocal()
    try:
        log = email_service.send_email(db, "someone@example.com", "Real SMTP test", "Body text")
        db.commit()
        assert log.status == EmailDeliveryStatus.ACCEPTED
        assert log.error is None
    finally:
        db.close()

    assert len(handler.messages) == 1
    assert handler.messages[0]["Subject"] == "Real SMTP test"
    assert handler.messages[0]["To"] == "someone@example.com"


def test_smtp_send_records_failed_when_the_server_is_unreachable(client, monkeypatch):
    from app.db.session import SessionLocal

    settings = get_settings()
    monkeypatch.setattr(settings, "email_provider", "smtp")
    monkeypatch.setattr(settings, "smtp_host", "127.0.0.1")
    monkeypatch.setattr(settings, "smtp_port", 1)  # nothing listens here
    monkeypatch.setattr(settings, "smtp_use_tls", False)

    db = SessionLocal()
    try:
        log = email_service.send_email(db, "someone@example.com", "Test", "Body")
        db.commit()
        assert log.status == EmailDeliveryStatus.FAILED
        assert log.error is not None
    finally:
        db.close()


def test_retry_failed_email_succeeds_once_the_server_is_back(client, smtp_server, smtp_settings, monkeypatch):
    """Simulates exactly the scenario Task 2 asks for: a failed send, then
    a successful retry -- the retry reuses the SAME log row/dedup key,
    never creating a duplicate."""
    from app.db.session import SessionLocal

    _controller, handler = smtp_server
    settings = get_settings()
    db = SessionLocal()
    try:
        # First attempt: point at a dead port so it fails.
        monkeypatch.setattr(settings, "smtp_port", 1)
        log = email_service.send_email(db, "retry@example.com", "Retry me", "Body", dedup_key="retry-test-1")
        db.commit()
        assert log.status == EmailDeliveryStatus.FAILED
        log_id = log.id

        # The server is back (or, here, we point back at the real one).
        monkeypatch.setattr(settings, "smtp_port", _controller.port)
        retried = email_service.retry_failed_email(db, log_id)
        assert retried.id == log_id
        assert retried.status == EmailDeliveryStatus.ACCEPTED
    finally:
        db.close()

    assert len(handler.messages) == 1


def test_retry_refuses_a_send_that_never_failed(client):
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        log = email_service.send_email(db, "already-sent@example.com", "Test", "Body")
        db.commit()
        with pytest.raises(ValueError, match="FAILED"):
            email_service.retry_failed_email(db, log.id)
    finally:
        db.close()
