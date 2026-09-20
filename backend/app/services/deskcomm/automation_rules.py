# -*- coding: utf-8 -*-
"""轻量 WHEN/IF/THEN 自动化（Deskcomm 规则层 → 优丁任务面，不抢 Hermes 主权）。"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

# 规则存内存 + 可选 PG（settings 键 automation_rules）；重启可从租户 settings 恢复
_RULES: dict[str, list[dict[str, Any]]] = {}

VALID_WHEN = frozenset(
    {
        "inquiry.created",
        "inquiry.replied",
        "sales_task.overdue",
        "message.stop",
        "payment.success",
        "pipeline.moved",
    }
)
VALID_THEN = frozenset(
    {
        "create_sales_task",
        "hermes_intent",
        "handoff",
        "set_vocabulary",
    }
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def list_rules(tenant_id: str) -> list[dict[str, Any]]:
    return list(_RULES.get(str(tenant_id), []))


def _validate_rule(rule: dict[str, Any]) -> dict[str, Any]:
    when = str(rule.get("when") or "").strip()
    raw_then = rule.get("then")
    if isinstance(raw_then, dict):
        then_obj = dict(raw_then)
    else:
        then_obj = {"action": str(raw_then or "")}
    action = str(then_obj.get("action") or "").strip()
    if when not in VALID_WHEN:
        raise ValueError(f"invalid_when:{when}")
    if action not in VALID_THEN:
        raise ValueError(f"invalid_then:{action}")
    cond = rule.get("if") or {}
    if cond is None:
        cond = {}
    if not isinstance(cond, dict):
        raise ValueError("if_must_be_object")
    out = {
        "id": str(rule.get("id") or uuid4()),
        "name": str(rule.get("name") or when),
        "when": when,
        "if": cond,
        "then": {**then_obj, "action": action},
        "enabled": bool(rule.get("enabled", True)),
        "created_at": rule.get("created_at") or _now(),
    }
    return out


def upsert_rule(tenant_id: str, rule: dict[str, Any]) -> dict[str, Any]:
    tid = str(tenant_id or "").strip()
    if not tid:
        raise ValueError("missing_tenant")
    row = _validate_rule(rule)
    rules = _RULES.setdefault(tid, [])
    for i, r in enumerate(rules):
        if r.get("id") == row["id"]:
            rules[i] = row
            return row
    rules.append(row)
    return row


def delete_rule(tenant_id: str, rule_id: str) -> bool:
    tid = str(tenant_id or "")
    rules = _RULES.get(tid, [])
    before = len(rules)
    _RULES[tid] = [r for r in rules if r.get("id") != rule_id]
    return len(_RULES[tid]) < before


def _match_if(cond: dict[str, Any], event: dict[str, Any]) -> bool:
    if not cond:
        return True
    payload = event.get("payload") or {}
    for k, v in cond.items():
        actual = payload.get(k, event.get(k))
        if isinstance(v, dict):
            if "eq" in v and actual != v["eq"]:
                return False
            if "ne" in v and actual == v["ne"]:
                return False
            if "contains" in v and str(v["contains"]) not in str(actual or ""):
                return False
        else:
            if actual != v:
                return False
    return True


def evaluate_event(
    db,
    tenant_id: str,
    event: dict[str, Any],
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    """评估事件 → 命中动作结果列表。

    - create_sales_task：写入 SalesTask（status=open, priority 可配）
    - hermes_intent：返回 intent 载荷（由调用方/门禁决定是否派发，避免静默抢调度）
    - handoff：返回 handoff 标记（不外发）
    - set_vocabulary：调用 pipeline_vocabulary
    """
    when = str(event.get("when") or event.get("event") or "").strip()
    hits: list[dict[str, Any]] = []
    for rule in list_rules(tenant_id):
        if not rule.get("enabled"):
            continue
        if rule.get("when") != when:
            continue
        if not _match_if(rule.get("if") or {}, event):
            continue
        action = str((rule.get("then") or {}).get("action") or "")
        params = {k: v for k, v in (rule.get("then") or {}).items() if k != "action"}
        outcome: dict[str, Any] = {
            "rule_id": rule.get("id"),
            "rule_name": rule.get("name"),
            "action": action,
            "params": params,
            "dry_run": dry_run,
            "at": _now(),
        }
        try:
            if action == "create_sales_task":
                title = str(params.get("title") or f"[auto:{when}] {rule.get('name')}")
                if dry_run:
                    outcome["result"] = {"would_create": True, "title": title}
                else:
                    from app.models.sales_task import SalesTask

                    t = SalesTask(
                        title=title[:500],
                        description=str(params.get("description") or f"automation rule {rule.get('id')}"),
                        task_type=str(params.get("task_type") or "followup"),
                        priority=str(params.get("priority") or "normal"),
                        tenant_id=str(tenant_id),
                        created_by=f"automation:{rule.get('id')}",
                    )
                    db.add(t)
                    db.commit()
                    db.refresh(t)
                    outcome["result"] = {"sales_task_id": str(t.id), "title": t.title, "status": t.status}
            elif action == "hermes_intent":
                intent = str(params.get("intent") or "询盘跟进")
                outcome["result"] = {
                    "dispatch": False,
                    "intent": intent,
                    "payload": params.get("payload") or {},
                    "note": "hermes 意图已生成；请经 golden-path/from-intent 显式派发（防暗驱）",
                }
            elif action == "handoff":
                from app.services.deskcomm.stop_handoff import detect_stop

                text = str(event.get("payload", {}).get("text") or params.get("reason") or "")
                outcome["result"] = {**detect_stop(text), "handoff": True, "sent": False}
            elif action == "set_vocabulary":
                from app.services.deskcomm.pipeline_vocabulary import set_vocabulary

                patch = params.get("vocabulary") or params
                if dry_run:
                    outcome["result"] = {"would_set": patch}
                else:
                    outcome["result"] = set_vocabulary(db, tenant_id, patch)
            else:
                outcome["result"] = {"error": f"unsupported_action:{action}"}
        except Exception as exc:  # noqa: BLE001
            outcome["result"] = {"error": str(exc)[:300]}
            logger.warning("automation evaluate failed rule=%s: %s", rule.get("id"), exc)
        hits.append(outcome)
    return {
        "tenant_id": str(tenant_id),
        "when": when,
        "matched": len(hits),
        "hits": hits,
        "rule_count": len(list_rules(tenant_id)),
    }
