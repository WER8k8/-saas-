# -*- coding: utf-8 -*-
"""WhatsApp STOP/退订 → 人接手（禁止自动再发）。"""
from __future__ import annotations

import re
from typing import Any

_STOP_PATTERNS = (
    r"(?i)\bstop\b",
    r"(?i)\bunsubscribe\b",
    r"(?i)\bopt[\s-]?out\b",
    r"退订",
    r"不要再发",
    r"别再发",
    r"停止发送",
    r"拒收",
)


def detect_stop(text: str | None) -> dict[str, Any]:
    raw = (text or "").strip()
    if not raw:
        return {"stop": False, "handoff": False, "sent": False, "reason": "empty"}
    for pat in _STOP_PATTERNS:
        if re.search(pat, raw):
            return {
                "stop": True,
                "handoff": True,
                "sent": False,
                "reason": "stop_keyword",
                "matched": pat,
                "note": "命中退订/STOP：禁止自动外发，转人工",
            }
    return {"stop": False, "handoff": False, "sent": False, "reason": "no_match"}
