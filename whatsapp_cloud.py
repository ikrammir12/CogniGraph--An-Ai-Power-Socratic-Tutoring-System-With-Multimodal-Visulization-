"""Secure, opt-in WhatsApp Cloud API client for CogniGraph."""
import hashlib
import hmac
import json
import os
import re
import urllib.error
import urllib.request


class WhatsAppAPIError(RuntimeError):
    def __init__(self, message, http_status=None, error_code=None):
        super().__init__(message)
        self.http_status = http_status
        self.error_code = str(error_code or "")


class LiveSendingDisabled(WhatsAppAPIError):
    pass


def live_sending_enabled():
    return os.getenv(
        "COGNIGRAPH_WHATSAPP_SEND_ENABLED", "false"
    ).strip().lower() == "true"


def send_template_message(recipient, parameters=None):
    """Send an approved template only when live sending is explicitly enabled.

    `parameters` must match the body placeholders in the approved template.
    An empty/None parameter list supports templates such as hello_world.
    """
    if not live_sending_enabled():
        raise LiveSendingDisabled(
            "WhatsApp sending is disabled; no message was sent."
        )

    token = os.getenv("COGNIGRAPH_WHATSAPP_ACCESS_TOKEN", "").strip()
    phone_id = os.getenv("COGNIGRAPH_WHATSAPP_PHONE_NUMBER_ID", "").strip()
    version = os.getenv("COGNIGRAPH_WHATSAPP_GRAPH_VERSION", "").strip()
    template = os.getenv(
        "COGNIGRAPH_WHATSAPP_TEMPLATE_NAME", "cognigraph_study_reminder"
    ).strip()
    language = os.getenv(
        "COGNIGRAPH_WHATSAPP_TEMPLATE_LANGUAGE", "en_US"
    ).strip()

    missing = [
        name for name, value in (
            ("COGNIGRAPH_WHATSAPP_ACCESS_TOKEN", token),
            ("COGNIGRAPH_WHATSAPP_PHONE_NUMBER_ID", phone_id),
            ("COGNIGRAPH_WHATSAPP_GRAPH_VERSION", version),
        ) if not value
    ]
    if missing:
        raise WhatsAppAPIError(
            "Missing required configuration: " + ", ".join(missing)
        )

    if not re.fullmatch(r"\d{5,30}", phone_id):
        raise WhatsAppAPIError("Invalid WhatsApp Phone Number ID.")
    if not re.fullmatch(r"v\d+\.\d+", version):
        raise WhatsAppAPIError(
            "Graph API version must look like vXX.0 and be supported by Meta."
        )
    if not re.fullmatch(r"[a-z0-9_]{1,512}", template):
        raise WhatsAppAPIError("Invalid WhatsApp template name.")
    if not re.fullmatch(r"[a-zA-Z0-9_]+", language):
        raise WhatsAppAPIError("Invalid template language code.")

    recipient = str(recipient or "").strip()
    if not re.fullmatch(r"\+[1-9]\d{7,14}", recipient):
        raise WhatsAppAPIError(
            "Recipient must be a valid international number, e.g. +923001234567."
        )

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient[1:],
        "type": "template",
        "template": {
            "name": template,
            "language": {"code": language},
        },
    }

    if parameters:
        payload["template"]["components"] = [{
            "type": "body",
            "parameters": [
                {"type": "text", "text": str(value)}
                for value in parameters
            ],
        }]

    url = f"https://graph.facebook.com/{version}/{phone_id}/messages"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            status_code = response.status
            raw_response = response.read()
    except urllib.error.HTTPError as exc:
        # Never include request headers or the access token in errors.
        raw_error = exc.read().decode("utf-8", errors="replace")
        try:
            details = json.loads(raw_error).get("error", {})
        except (ValueError, AttributeError):
            details = {}
        code = details.get("code", "")
        message = str(details.get("message") or "Meta rejected the request")
        raise WhatsAppAPIError(
            f"Meta API returned HTTP {exc.code}: {message}",
            http_status=exc.code,
            error_code=code,
        ) from None
    except (urllib.error.URLError, TimeoutError) as exc:
        # A timeout may be ambiguous. Do not automatically resend.
        raise WhatsAppAPIError(
            f"Meta API request failed or timed out: {type(exc).__name__}"
        ) from None

    try:
        result = json.loads(raw_response.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise WhatsAppAPIError(
            f"Meta returned HTTP {status_code} with invalid JSON."
        ) from None

    messages = result.get("messages") or []
    message_id = messages[0].get("id") if messages else None
    if status_code < 200 or status_code >= 300 or not message_id:
        raise WhatsAppAPIError(
            "Meta response did not contain a message ID.",
            http_status=status_code,
        )

    return {
        "message_id": str(message_id),
        "api_status": status_code,
    }


def verify_webhook_signature(raw_body, signature_header, app_secret=None):
    """Verify Meta's X-Hub-Signature-256 against the exact request bytes."""
    secret = (
        app_secret
        if app_secret is not None
        else os.getenv("COGNIGRAPH_WHATSAPP_APP_SECRET", "")
    )
    if not secret or not signature_header:
        return False

    expected = "sha256=" + hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature_header.strip())


def parse_status_events(payload):
    """Extract WhatsApp message status events from a webhook payload."""
    events = []
    if not isinstance(payload, dict):
        return events

    for entry in payload.get("entry", []):
        if not isinstance(entry, dict):
            continue

        waba_id = str(entry.get("id") or "")
        for change in entry.get("changes", []):
            if not isinstance(change, dict) or change.get("field") != "messages":
                continue

            value = change.get("value") or {}
            if value.get("messaging_product") != "whatsapp":
                continue

            metadata = value.get("metadata") or {}
            phone_id = str(metadata.get("phone_number_id") or "")

            for item in value.get("statuses", []):
                if not isinstance(item, dict):
                    continue

                errors = item.get("errors") or []
                error = errors[0] if errors else {}
                try:
                    timestamp = float(item.get("timestamp"))
                except (TypeError, ValueError):
                    timestamp = None

                events.append({
                    "waba_id": waba_id,
                    "phone_number_id": phone_id,
                    "message_id": str(item.get("id") or ""),
                    "status": str(item.get("status") or "").lower(),
                    "timestamp": timestamp,
                    "error_code": str(error.get("code") or ""),
                    "error_message": str(
                        error.get("title") or error.get("message") or
                        (error.get("error_data") or {}).get("details") or ""
                    ),
                })

    return events
