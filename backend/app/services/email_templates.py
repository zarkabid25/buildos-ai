"""Phase 9.1 (Task 3): the five required transactional email templates.
Plain-text subject/body pairs, filled with `.format(**context)` -- no
HTML/MJML renderer exists in this app and adding one isn't required to
satisfy "templates for essential emails." Every template's required
context keys are documented so a caller gets a clear KeyError in
development rather than a silently mangled email in production."""

from dataclasses import dataclass


@dataclass(frozen=True)
class EmailTemplate:
    subject: str
    body: str


TEMPLATES: dict[str, EmailTemplate] = {
    "account_invitation": EmailTemplate(
        subject="You've been invited to join {org_name} on BuildOS AI",
        body=(
            "Hi,\n\n{inviter_name} has invited you to join {org_name} on BuildOS AI as {role}.\n\n"
            "Accept your invitation here: {accept_url}\n\nThis link expires on {expires_at}.\n\n-- BuildOS AI"
        ),
    ),
    "password_reset": EmailTemplate(
        subject="Reset your BuildOS AI password",
        body=(
            "Hi {full_name},\n\nWe received a request to reset your password. If this was you, "
            "use this link within {valid_hours} hours: {reset_url}\n\n"
            "If you didn't request this, you can safely ignore this email -- your password hasn't changed.\n\n-- BuildOS AI"
        ),
    ),
    "supplier_onboarding": EmailTemplate(
        subject="Your BuildOS AI marketplace application: {status}",
        body=(
            "Hi {contact_name},\n\nYour application for {supplier_name} to join the BuildOS AI marketplace "
            "has been {status}.\n\n{detail}\n\n-- BuildOS AI"
        ),
    ),
    "billing_notification": EmailTemplate(
        subject="BuildOS AI billing: {event}",
        body="Hi,\n\n{event} for {company_name}.\n\n{detail}\n\nView your billing details: {billing_url}\n\n-- BuildOS AI",
    ),
    "support_update": EmailTemplate(
        subject="Update on your support ticket: {ticket_subject}",
        body="Hi,\n\nThere's a new update on your support ticket \"{ticket_subject}\":\n\n{detail}\n\n-- BuildOS AI",
    ),
}
