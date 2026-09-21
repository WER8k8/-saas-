# -*- coding: utf-8 -*-
"""AI 预算闸 — 复用 wallet_guard/token_ledger，可选月度 Token 上限。"""
from __future__ import annotations

import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _monthly_cap() -> Optional[int]:
    for key in ("AI_SALES_MONTHLY_TOKEN_CAP", "AI_MONTHLY_TOKEN_CAP"):
        v = os.getenv(key)
        if v is not None and str(v).strip() != "":
            try:
                return int(float(v))
            except ValueError:
                continue
        try:
            from app.core.config import settings

            sv = getattr(settings, key, None)
            if sv not in (None, ""):
                return int(float(sv))
        except Exception:  # noqa: BLE001
            continue
    return None


def _month_consumed(db: Any, tenant_id: str) -> Optional[int]:
    """当月 meter/token 消耗：有库则读，无库返回 None（不编造）。"""
    if db is None or not hasattr(db, "query"):
        return None
    try:
        from datetime import datetime, timezone

        from app.models.token_ledger import TokenLedgerEntry
        from app.services.acquisition.repo import resolve_tenant_uuid

        tid = resolve_tenant_uuid(db, tenant_id) or tenant_id
        month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        rows = list(db.query(TokenLedgerEntry).filter(TokenLedgerEntry.tenant_id == tid).all())
        used = 0
        seen = False
        for r in rows:
            created = getattr(r, "created_at", None)
            if created is not None:
                try:
                    if created < month_start:
                        continue
                except TypeError:
                    pass
            delta = getattr(r, "amount", None) or getattr(r, "delta", None) or 0
            try:
                d = int(delta)
            except (TypeError, ValueError):
                d = 0
            if d < 0:
                used += -d
                seen = True
        return used if seen or rows else (0 if rows else None)
    except Exception as exc:  # noqa: BLE001
        logger.warning("ai_budget month consumed read failed: %s", exc)
        return None


def check_ai_budget(tenant_id: str, db: Any = None) -> dict[str, Any]:
    """AI 销售动作前预算检查。硬拦以 wallet_guard 为准，禁止假余额。"""
    from app.services.acquisition.wallet_guard import check_wallet_status

    resolved_db = db
    if resolved_db is None or type(resolved_db).__name__ == "Depends" or not hasattr(resolved_db, "query"):
        resolved_db = None

    wallet = check_wallet_status(tenant_id=tenant_id, db=resolved_db) or {}
    hard_block = bool(wallet.get("hard_block_enabled"))
    cap = _monthly_cap()
    consumed = _month_consumed(resolved_db, tenant_id) if resolved_db is not None else None

    blocked = hard_block
    reason = "wallet_hard_block" if hard_block else "ok"
    if not blocked and cap is not None and consumed is not None and consumed >= cap:
        blocked = True
        reason = "monthly_token_cap_exceeded"

    return {
        "allowed": not blocked,
        "blocked": blocked,
        "reason": reason,
        "hard_block_enabled": hard_block,
        "wallet": {
            "balance": wallet.get("balance"),
            "source": wallet.get("source"),
            "status": wallet.get("status"),
        },
        "monthly_cap": cap,
        "monthly_consumed": consumed,
        "note": "无账本时不编造余额；超限诚实拦截",
    }
