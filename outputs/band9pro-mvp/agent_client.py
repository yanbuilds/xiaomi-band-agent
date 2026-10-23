"""Grok/webhook adapter for the local Band Agent API.

The adapter only sends parsed health events.  It never receives or stores a
Bluetooth auth key.  The webhook body is signed as ``timestamp + '.' + body``
with HMAC-SHA256 so a self-hosted Grok runner can reject replayed requests.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class AgentConfig:
    local_api: str
    agent_token: str
    webhook_url: str
    webhook_secret: str
    timeout: float = 15.0

    def validate(self) -> None:
        if not self.local_api.startswith("https://") and not self.local_api.startswith("http://127.0.0.1"):
            raise ValueError("local_api must use HTTPS, except loopback development URLs")
        if len(self.agent_token) < 24 or len(self.webhook_secret) < 24:
            raise ValueError("tokens/secrets must be at least 24 characters")
        if not self.webhook_url.startswith("https://"):
            raise ValueError("webhook_url must use HTTPS")


def signed_headers(body: bytes, secret: str, timestamp: int) -> dict[str, str]:
    message = f"{timestamp}.".encode() + body
    digest = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    return {
        "Content-Type": "application/json",
        "X-Band-Agent-Timestamp": str(timestamp),
        "X-Band-Agent-Signature": f"sha256={digest}",
    }


def verify_signature(body: bytes, secret: str, timestamp: str, signature: str,
                     now: int | None = None, max_age: int = 300) -> bool:
    try:
        ts = int(timestamp)
    except (TypeError, ValueError):
        return False
    current = int(time.time()) if now is None else now
    if abs(current - ts) > max_age or not signature.startswith("sha256="):
        return False
    expected = signed_headers(body, secret, ts)["X-Band-Agent-Signature"]
    return hmac.compare_digest(expected, signature)


class AgentRunner:
    """Process one bounded batch; callers schedule it with WorkManager/cron."""

    def __init__(self, config: AgentConfig, client: httpx.Client | None = None):
        config.validate()
        self.config = config
        self.client = client or httpx.Client(timeout=config.timeout)

    def close(self) -> None:
        self.client.close()

    def run_once(self, limit: int = 20) -> dict[str, int]:
        response = self.client.get(
            self.config.local_api.rstrip("/") + "/v1/agent/pending",
            headers={"Authorization": "Bearer " + self.config.agent_token},
            params={"limit": min(max(limit, 1), 20)},
        )
        response.raise_for_status()
        events = response.json()
        completed = 0
        failed = 0
        for event in events:
            try:
                result = self._ask_webhook(event)
                self._store_result(event["event_id"], result)
                completed += 1
            except (httpx.HTTPError, KeyError, TypeError, ValueError):
                # Leave the event pending so the next scheduled run can retry.
                failed += 1
        return {"seen": len(events), "completed": completed, "failed": failed}

    def _ask_webhook(self, event: dict[str, Any]) -> dict[str, Any]:
        # Deliberately send only the parsed event; no phone, MAC, token or key.
        body = json.dumps({"event": event}, ensure_ascii=False, separators=(",", ":")).encode()
        timestamp = int(time.time())
        response = self.client.post(
            self.config.webhook_url,
            content=body,
            headers=signed_headers(body, self.config.webhook_secret, timestamp),
        )
        response.raise_for_status()
        result = response.json()
        if not isinstance(result, dict):
            raise ValueError("webhook result must be an object")
        return result

    def _store_result(self, event_id: str, result: dict[str, Any]) -> None:
        response = self.client.post(
            self.config.local_api.rstrip("/") + "/v1/agent/results/" + event_id,
            json=result,
            headers={"Authorization": "Bearer " + self.config.agent_token},
        )
        response.raise_for_status()


__all__ = ["AgentConfig", "AgentRunner", "signed_headers", "verify_signature"]
