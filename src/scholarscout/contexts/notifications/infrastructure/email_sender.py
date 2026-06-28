"""
Email sender — aiosmtplib async SMTP with Jinja2 templates.

Supports:
- SMTP (local MailHog / dev)
- SendGrid (production)
- AWS SES (production)
"""

from __future__ import annotations

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import aiosmtplib
from jinja2 import Environment, PackageLoader, select_autoescape

from scholarscout.config import settings
from scholarscout.shared.infrastructure.telemetry.metrics import notifications_sent_total

logger = logging.getLogger(__name__)

_DIGEST_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>ScholarScout Digest</title></head>
<body style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
  <h1 style="color: #1a56db;">ScholarScout</h1>
  <h2>New opportunities for: {{ subscription_name }}</h2>
  <p>Hello {{ to_name }},</p>
  <p>Here are the latest graduate funding opportunities matching your search:</p>

  {% for opp in opportunities %}
  <div style="border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; margin: 16px 0;">
    <h3 style="margin: 0 0 8px; color: #111827;">{{ opp.title }}</h3>
    <p style="margin: 0 0 4px;"><strong>University:</strong> {{ opp.university_name }} ({{ opp.country }})</p>
    <p style="margin: 0 0 4px;"><strong>Degree:</strong> {{ opp.degree_level }}</p>
    <p style="margin: 0 0 4px;"><strong>Funding:</strong> {{ opp.funding_type.replace('_', ' ').title() }}</p>
    {% if opp.stipend_amount %}<p style="margin: 0 0 4px;"><strong>Stipend:</strong> ${{ "{:,.0f}".format(opp.stipend_amount) }}/year</p>{% endif %}
    {% if opp.deadline %}<p style="margin: 0 0 8px;"><strong>Deadline:</strong> {{ opp.deadline }}</p>{% endif %}
    <p style="color: #6b7280; font-size: 14px;">{{ opp.description[:300] }}{% if opp.description|length > 300 %}...{% endif %}</p>
  </div>
  {% endfor %}

  <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 32px 0;">
  <p style="color: #9ca3af; font-size: 12px;">
    You're receiving this because you subscribed to scholarship alerts at ScholarScout.
    <a href="https://scholarscout.io/unsubscribe" style="color: #9ca3af;">Unsubscribe</a>
  </p>
</body>
</html>
"""


class EmailSender:
    async def send_digest(
        self,
        to_email: str,
        to_name: str,
        subscription_name: str,
        opportunities: list[Any],
    ) -> None:
        from jinja2 import Template
        template = Template(_DIGEST_TEMPLATE)
        html_body = template.render(
            to_name=to_name or "Scholar",
            subscription_name=subscription_name,
            opportunities=opportunities,
        )
        subject = f"ScholarScout: {len(opportunities)} new opportunities for '{subscription_name}'"
        await self.send_raw(to_email=to_email, subject=subject, html_body=html_body)

    async def send_raw(self, to_email: str, subject: str, html_body: str) -> None:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{settings.email.from_name} <{settings.email.from_email}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, "html"))

        try:
            await aiosmtplib.send(
                msg,
                hostname=settings.email.host,
                port=settings.email.port,
                username=settings.email.username or None,
                password=settings.email.password or None,
                use_tls=settings.email.use_tls,
            )
            notifications_sent_total.labels(channel="email", status="success").inc()
            logger.info("Email sent to %s: %s", to_email, subject)
        except Exception as e:
            notifications_sent_total.labels(channel="email", status="error").inc()
            logger.error("Failed to send email to %s: %s", to_email, e)
            raise
