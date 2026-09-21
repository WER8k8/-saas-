# -*- coding: utf-8 -*-
"""出站 WhatsApp 守卫：STOP 检测 + 固定窗口节流（Deskcomm 反封策略并入）。"""
from __future__ import annotations

import re
import time
from typing import Any

STOP_PATTERN = re.compile(
    r"^(stop|unsubscribe|cancel|opt\s*out|退订|取消订阅|别再发|不要再发|拒绝接收)$",
    re.I,
)

# in-process throttle: (tenant_id, phone) -> [timestamps]
_OUTBOUND_LOG: dict[tuple[str, str], list[float]] = {}

DEFAULT_MAX_PER_WINDOW = 5
DEFAULT_WINDOW_SECONDS = 60.0


def detect_stop(text: str) -> bool:
    t = (text or "").strip()
    return bool(t and STOP_PATTERN.match(t))


def check_outbound_guard(
    *,
    tenant_id: str,
    phone: str,
    text: str = "",
    suppressed: bool = False,
    max_per_window: int = DEFAULT_MAX_PER_WINDOW,
    window_seconds: float = DEFAULT_WINDOW_SECONDS,
    now: float | None = None,
) -> dict[str, Any]:
    """出站前检查：STOP/已抑制 → suppress；超频 → throttle。"""
    if detect_stop(text) or suppressed:
        return {
            "allow": False,
            "action": "suppress",
            "reason": "stop_keyword" if detect_stop(text) else "already_suppressed",
        }
    ts = now if now is not None else time.time()
    key = (str(tenant_id or ""), str(phone or ""))
    window = [t for t in _OUTBOUND_LOG.get(key, []) if ts - t < float(window_seconds)]
    if len(window) >= int(max_per_window):
        _OUTBOUND_LOG[key] = window
        return {
            "allow": False,
            "action": "throttle",
            "reason": "rate_limited",
            "window_count": len(window),
            "max_per_window": max_per_window,
            "window_seconds": window_seconds,
        }
    window.append(ts)
    _OUTBOUND_LOG[key] = window
    return {
        "allow": True,
        "action": "send",
        "reason": "ok",
        "window_count": len(window),
        "max_per_window": max_per_window,
    }


def mark_suppressed(_tenant_id: str, _phone: str) -> None:
    """预留：持久化抑制名单由调用方写库；进程内节流日志清空。"""
    _OUTBOUND_LOG.pop((str(_tenant_id or ""), str(_phone or "")), None)
