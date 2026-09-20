# -*- coding: utf-8 -*-
"""AI Agent 一等指派 + 租户预算闸 + 动作审计（Deskcomm 模式并入 UJ）。"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

AGENT_PREFIX = "agent:"
USER_PREFIX = "user:"

# 无外部 Key 时 Agent 动作只允许「本地可完成」类型，禁止假外发
ALLOWED_OFFLINE_AGENT_ACTIONS = frozenset(
    {
        "schedule_followup",
        "create_sales_task",
        "handoff_note",
        "tag_inquiry",
        "pipeline_move",
        "hermes_intent",
    }
)


def normalize_assignee(raw: str | None) -> dict[str, Any]:
    """将指派人归一为 user:* 或 agent:*；未知形态诚实拒绝。"""
    s = (raw or "").strip()
    if not s:
        return {"ok": False, "error": "empty_assignee"}
    low = s.lower()
    if low.startswith(AGENT_PREFIX):
        return {"ok": True, "kind": "agent", "id": s, "agent_name": s[len(AGENT_PREFIX) :]}
    if low.startswith(USER_PREFIX):
        return {"ok": True, "kind": "user", "id": s, "agent_name": None}
    # 允许裸 UUID/用户名 → user
    return {"ok": True, "kind": "user", "id": s if low.startswith(USER_PREFIX) else f"{USER_PREFIX}{s}", "agent_name": None}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def agent_budget_allow(db, tenant_id: str, *, cost_units: int = 1) -> dict[str, Any]:
    """租户 Agent 预算闸。

    策略：优先读 tenant.settings JSON 的 agent_budget；缺省时用 ai_quota 余量近似；
    都不可用时 **allow 但标注 unknown**（不假装有预算，也不无故拦交互）。
    """
    tid = str(tenant_id or "").strip()
    if not tid:
        return {"allow": False, "reason": "missing_tenant", "source": "none"}
    try:
        from app.models.tenant import Tenant

        row = db.query(Tenant).filter(Tenant.id == tid).first()
        if not row:
            return {"allow": False, "reason": "tenant_not_found", "source": "none"}
        settings: dict[str, Any] = {}
        if row.settings:
            try:
                settings = json.loads(row.settings) if isinstance(row.settings, str) else dict(row.settings)
            except Exception:
                settings = {}
        budget = settings.get("agent_budget") or {}
        if isinstance(budget, dict) and ("monthly_limit" in budget or "remaining" in budget):
            remaining = budget.get("remaining")
            limit = budget.get("monthly_limit")
            used = budget.get("used", 0)
            if remaining is None and limit is not None:
                remaining = max(0, int(limit) - int(used or 0))
            if remaining is not None and int(remaining) < cost_units:
                return {
                    "allow": False,
                    "reason": "agent_budget_exceeded",
                    "remaining": remaining,
                    "limit": limit,
                    "source": "agent_budget",
                }
            return {
                "allow": True,
                "remaining": remaining,
                "limit": limit,
                "source": "agent_budget",
            }
        # 近似：套餐 AI 配额
        used = int(getattr(row, "ai_quota_used", 0) or 0)
        total = int(getattr(row, "max_ai_quota", 0) or 0) or int(getattr(row, "ai_quota_total", 0) or 0)
        if total > 0 and used + cost_units > total:
            return {
                "allow": False,
                "reason": "ai_quota_exceeded",
                "used": used,
                "limit": total,
                "source": "ai_quota_approx",
            }
        return {
            "allow": True,
            "used": used,
            "limit": total or None,
            "source": "ai_quota_approx" if total else "unknown_open",
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("agent_budget_allow error tenant=%s: %s", tid, exc)
        return {"allow": True, "reason": f"budget_check_error:{exc}", "source": "error_open"}


def record_agent_action(
    db,
    *,
    tenant_id: str,
    agent_id: str,
    action: str,
    target: str = "",
    payload: dict[str, Any] | None = None,
    result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Agent 动作审计：append-only 到 operation_logs 风格存储（表不存在则文件级日志兜底）。"""
    entry = {
        "id": str(uuid.uuid4()),
        "tenant_id": str(tenant_id or ""),
        "agent_id": str(agent_id or ""),
        "action": str(action or ""),
        "target": str(target or ""),
        "payload": payload or {},
        "result": result or {},
        "at": _now().isoformat(),
        "source": "deskcomm_agent_assignee",
    }
    logged = False
    try:
        from app.core.database import Base  # noqa: F401
        # 优先通用审计表（若模型存在）
        try:
            from app.models.operation_log import OperationLog  # type: ignore

            row = OperationLog(
                id=entry["id"],
                tenant_id=entry["tenant_id"] or None,
                operator=entry["agent_id"],
                action=entry["action"],
                resource=str(entry["target"])[:200],
                detail=json.dumps(entry, ensure_ascii=False)[:4000],
            )
            db.add(row)
            db.commit()
            logged = True
        except Exception:
            db.rollback()
    except Exception:
        logged = False
    if not logged:
        logger.info("agent_action_audit %s", json.dumps(entry, ensure_ascii=False))
    entry["persisted"] = logged
    return entry


def gate_agent_action(
    db,
    *,
    tenant_id: str,
    assignee: str | None,
    action: str,
    cost_units: int = 1,
) -> dict[str, Any]:
    """统一闸门：指派合法 + 动作类型 + 预算。"""
    norm = normalize_assignee(assignee)
    if not norm.get("ok"):
        return {"ok": False, "error": norm.get("error"), "stage": "assignee"}
    if norm["kind"] == "agent":
        if action not in ALLOWED_OFFLINE_AGENT_ACTIONS:
            return {
                "ok": False,
                "error": "agent_action_not_allowed_offline",
                "action": action,
                "stage": "action_allowlist",
            }
        budget = agent_budget_allow(db, tenant_id, cost_units=cost_units)
        if not budget.get("allow"):
            return {"ok": False, "error": budget.get("reason"), "budget": budget, "stage": "budget"}
        return {"ok": True, "assignee": norm, "budget": budget}
    return {"ok": True, "assignee": norm, "budget": None}
