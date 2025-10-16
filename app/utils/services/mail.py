from flask import current_app as app
import requests
from typing import Optional

SMS_DEFAULT_ENDPOINT = "https://rpcapplication.aiims.edu/services/api/v1/mail/single"


def send_mail(email: str, subject: str, body: str) -> int:
    """
    Send an email via REST JSON endpoint.

    Args:
        mobile: Recipient mobile number (E.164 or local as accepted by provider).
        message: Text message content.

    Returns:
        HTTP status code from upstream (200 expected on success) or:
        400 for local validation failure,
        500 for internal/request exception,
        503 when service disabled.
    """
    if not email or not subject or not body:
        app.logger.warning("send_mail: missing email, subject or body")
        return 400

    # Feature flag: if MAIL_FLAG disabled, skip real send
    if not app.config.get("MAIL_FLAG", True):
        app.logger.info(
            "send_mail: skipped (MAIL_FLAG disabled) email=%s subject=%r body=%r", email, subject, body)
        return 200

    url = app.config.get("MAIL_API_URL", SMS_DEFAULT_ENDPOINT)
    token = (
        app.config.get("MAIL_API_TOKEN")
    )

    if not token:
        app.logger.error(
            "send_mail: missing API token (MAIL_API_TOKEN)")
        return 503

    payload = {
        "to": email,
        "subject": subject,
        "body": body,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    try:
        app.logger.debug("send_sms: POST %s payload=%s", url, payload)
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
    except requests.RequestException as exc:
        app.logger.error(
            "send_mail: request exception email=%s err=%s", email, exc, exc_info=True)
        return 500

    if resp.status_code != 200:
        snippet = (resp.text or "")[:300]
        app.logger.warning(
            "send_mail: upstream failure status=%s body=%r email=%s",
            resp.status_code,
            snippet,
            email,
        )
    else:
        app.logger.info("send_mail: sent email=%s status=%s",
                        email, resp.status_code)
    return resp.status_code
