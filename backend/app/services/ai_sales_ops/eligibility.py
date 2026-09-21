# -*- coding: utf-8 -*-
"""AI 会话资格门禁 — 借鉴 Deskcomm elegibilidade，纯函数 deny 规则。

open：默认可接管（兼容已发布获客号）
allowlist：仅显式授权（测试号 / ai_authorized_at）
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

AI_GATE_MODES = ("open", "allowlist")

DEFAULT_ALLOWLIST_TTL_DAYS = 30


def normalize_gate_mode(raw: Any) -> str:
    return "allowlist" if raw == "allowlist" else "open"


def _to_dt(v: Any) -> Optional[datetime]:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v
    if isinstance(v, (int, float)):
        return datetime.fromtimestamp(float(v), tz=timezone.utc)
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("infinity", "inf", "never"):
            return datetime.max.replace(tzinfo=timezone.utc)
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


@dataclass
class EligibilityState:
    mode: str = "open"
    force_human: bool = False
    bot_silenced_until: Any = None
    assignee_kind: Optional[str] = None
    ai_authorized_at: Any = None
    phone: Optional[str] = None
    test_numbers: Optional[list[str]] = None
    now: Optional[datetime] = None
    ttl_days: int = DEFAULT_ALLOWLIST_TTL_DAYS

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "EligibilityState":
        return cls(
            mode=normalize_gate_mode(raw.get("mode") or raw.get("ai_gate")),
            force_human=bool(raw.get("force_human")),
            bot_silenced_until=raw.get("bot_silenced_until"),
            assignee_kind=raw.get("assignee_kind"),
            ai_authorized_at=raw.get("ai_authorized_at"),
            phone=raw.get("phone"),
            test_numbers=raw.get("test_numbers") or [],
            now=_to_dt(raw.get("now")),
            ttl_days=int(raw.get("ttl_days") or DEFAULT_ALLOWLIST_TTL_DAYS),
        )


def decide_eligibility(state: EligibilityState | dict[str, Any]) -> dict[str, Any]:
    st = state if isinstance(state, EligibilityState) else EligibilityState.from_dict(state)
    now = st.now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    if st.force_human:
        return {"allowed": False, "reason": "force_human", "mode": st.mode}
    if st.assignee_kind == "user":
        return {"allowed": False, "reason": "human_assignee", "mode": st.mode}
    silenced = _to_dt(st.bot_silenced_until)
    if silenced is not None and silenced >= now:
        return {"allowed": False, "reason": "bot_silenced", "mode": st.mode}

    if st.mode == "open":
        return {"allowed": True, "reason": "gate_open", "mode": st.mode}

    # allowlist
    nums = [str(x).strip() for x in (st.test_numbers or []) if str(x).strip()]
    if st.phone and st.phone.strip() in nums:
        return {"allowed": True, "reason": "test_number", "mode": st.mode}
    auth = _to_dt(st.ai_authorized_at)
    if auth is not None:
        ttl = datetime.fromtimestamp(auth.timestamp() + st.ttl_days * 86400, tz=timezone.utc)
        if ttl >= now:
            return {"allowed": True, "reason": "ai_authorized", "mode": st.mode}
        return {"allowed": False, "reason": "authorization_expired", "mode": st.mode}
    return {"allowed": False, "reason": "not_allowlisted", "mode": st.mode}
