from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass
class DeliveryResult:
    ok: bool
    status_code: int | None
    duration_ms: int
    response_preview: str
    error: str | None


def _sign(secret: str, body: bytes, timestamp: int) -> str:
    message = f"{timestamp}.".encode() + body
    digest = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _preview_text(text: str, limit: int = 200) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1] + "…"


def deliver_webhook(
    url: str,
    secret: str,
    event_type: str,
    payload: dict,
    *,
    timeout_seconds: float = 10.0,
) -> DeliveryResult:
    """向回调地址 POST JSON；返回投递结果。"""
    started = time.perf_counter()
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    timestamp = int(time.time())
    delivery_id = f"del_{uuid.uuid4().hex}"
    request = Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "gitmail-webhook/1.0",
            "X-Gitmail-Event": event_type,
            "X-Gitmail-Delivery": delivery_id,
            "X-Gitmail-Timestamp": str(timestamp),
            "X-Gitmail-Signature": _sign(secret, body, timestamp),
        },
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read(4096)
            status = int(response.status)
            preview = _preview_text(raw.decode("utf-8", errors="replace"))
            duration_ms = int((time.perf_counter() - started) * 1000)
            ok = 200 <= status < 300
            return DeliveryResult(
                ok=ok,
                status_code=status,
                duration_ms=duration_ms,
                response_preview=preview,
                error=None if ok else f"HTTP {status}",
            )
    except HTTPError as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        try:
            raw = exc.read(4096)
            preview = _preview_text(raw.decode("utf-8", errors="replace"))
        except Exception:
            preview = ""
        return DeliveryResult(
            ok=False,
            status_code=exc.code,
            duration_ms=duration_ms,
            response_preview=preview,
            error=f"HTTP {exc.code}",
        )
    except URLError as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        return DeliveryResult(
            ok=False,
            status_code=None,
            duration_ms=duration_ms,
            response_preview="",
            error=str(exc.reason),
        )
    except Exception as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        return DeliveryResult(
            ok=False,
            status_code=None,
            duration_ms=duration_ms,
            response_preview="",
            error=str(exc),
        )
