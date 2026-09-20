# -*- coding: utf-8 -*-
"""Deskcomm 式 CRM Sales-OS MCP 工具 — 只操作优丁 PG，不连 Deskcomm。"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

TOOL_MANIFEST: List[Dict[str, Any]] = [
    {
        "name": "crm_inquiry_list",
        "description": "列出租户询盘（只读）。Deskcomm 对齐：agent 可查上下文。",
        "input_schema": {
            "type": "object",
            "properties": {
                "tenant_id": {"type": "string"},
                "limit": {"type": "integer", "default": 20},
            },
            "required": ["tenant_id"],
        },
    },
    {
        "name": "crm_sales_task_create",
        "description": "创建销售跟进任务（可 agent:* 指派；走预算闸与审计）。",
        "input_schema": {
            "type": "object",
            "properties": {
                "tenant_id": {"type": "string"},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "assignee": {"type": "string", "description": "user:* 或 agent:*"},
                "priority": {"type": "string", "enum": ["high", "normal", "low"]},
            },
            "required": ["tenant_id", "title"],
        },
    },
    {
        "name": "crm_sales_task_assign",
        "description": "改销售任务指派（user/agent）。",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string"},
                "assignee": {"type": "string"},
            },
            "required": ["task_id", "assignee"],
        },
    },
    {
        "name": "crm_followup_schedule",
        "description": "安排跟进：创建 due 销售任务（followup）。",
        "input_schema": {
            "type": "object",
            "properties": {
                "tenant_id": {"type": "string"},
                "title": {"type": "string"},
                "due_at": {"type": "string"},
                "inquiry_id": {"type": "string"},
            },
            "required": ["tenant_id", "title"],
        },
    },
    {
        "name": "crm_pipeline_vocabulary",
        "description": "读取或更新租户 pipeline 词汇。",
        "input_schema": {
            "type": "object",
            "properties": {
                "tenant_id": {"type": "string"},
                "patch": {"type": "object"},
            },
            "required": ["tenant_id"],
        },
    },
    {
        "name": "crm_stop_check",
        "description": "检测消息是否 STOP/退订；命中则 handoff=true 且 sent=false。",
        "input_schema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
    {
        "name": "crm_capability_matrix",
        "description": "Deskcomm×优丁取舍矩阵（重叠不引入 / 不重叠并入）。",
        "input_schema": {"type": "object", "properties": {}},
    },
]


class CrmSalesOsTools:
    """工具执行器：db 必填才允许写路径。"""

    @classmethod
    def get_tool_manifest(cls) -> List[Dict[str, Any]]:
        return list(TOOL_MANIFEST)

    @classmethod
    async def call_tool(cls, name: str, arguments: Dict[str, Any], db=None) -> Dict[str, Any]:
        args = dict(arguments or {})
        if name == "crm_capability_matrix":
            from app.services.deskcomm.capability_matrix import matrix_report

            return {"status": "success", "matrix": matrix_report()}

        if name == "crm_stop_check":
            from app.services.deskcomm.stop_handoff import detect_stop

            return {"status": "success", **detect_stop(str(args.get("text") or ""))}

        if db is None:
            return {
                "status": "not_configured",
                "message": "CRM MCP 需要数据库会话才可读写优丁实体",
            }

        if name == "crm_inquiry_list":
            tid = str(args.get("tenant_id") or "")
            if not tid:
                return {"status": "failed", "error": "tenant_id_required"}
            try:
                from app.models.inquiry import Inquiry

                q = db.query(Inquiry)
                # 尽力按租户过滤；字段缺失时全表会过大 → 诚实说明
                if hasattr(Inquiry, "tenant_id"):
                    q = q.filter(Inquiry.tenant_id == tid)
                rows = q.order_by(Inquiry.created_at.desc()).limit(int(args.get("limit") or 20)).all()
                items = []
                for r in rows:
                    items.append(
                        {
                            "id": str(r.id),
                            "name": getattr(r, "name", None),
                            "status": getattr(r, "status", None),
                            "source": getattr(r, "source_channel", None),
                        }
                    )
                return {"status": "success", "items": items, "count": len(items), "tenant_id": tid}
            except Exception as exc:  # noqa: BLE001
                return {"status": "failed", "error": str(exc)[:300]}

        if name in ("crm_sales_task_create", "crm_followup_schedule"):
            from app.services.deskcomm.agent_assignee import gate_agent_action, record_agent_action
            from app.models.sales_task import SalesTask

            tid = str(args.get("tenant_id") or "")
            title = str(args.get("title") or "").strip()
            if not tid or not title:
                return {"status": "failed", "error": "tenant_id_and_title_required"}
            assignee = args.get("assignee") or "agent:deskcomm-crm"
            gate = gate_agent_action(db, tenant_id=tid, assignee=str(assignee), action="create_sales_task")
            if not gate.get("ok"):
                return {"status": "failed", "error": gate.get("error"), "gate": gate}
            due = args.get("due_at")
            due_dt = None
            if due:
                try:
                    from datetime import datetime

                    due_dt = datetime.fromisoformat(str(due).replace("Z", "+00:00"))
                except Exception:
                    due_dt = None
            t = SalesTask(
                title=title[:500],
                description=str(args.get("description") or args.get("inquiry_id") or "")[:2000],
                task_type="followup" if name == "crm_followup_schedule" else str(args.get("task_type") or "followup"),
                priority=str(args.get("priority") or "normal"),
                due_at=due_dt,
                assigned_to=str(assignee),
                tenant_id=tid,
                created_by=str(assignee),
            )
            db.add(t)
            db.commit()
            db.refresh(t)
            record_agent_action(
                db,
                tenant_id=tid,
                agent_id=str(assignee),
                action=name,
                target=str(t.id),
                payload=args,
                result={"status": t.status},
            )
            return {
                "status": "success",
                "sales_task_id": str(t.id),
                "title": t.title,
                "assignee": t.assigned_to,
                "task_status": t.status,
            }

        if name == "crm_sales_task_assign":
            from app.services.deskcomm.agent_assignee import gate_agent_action, record_agent_action, normalize_assignee
            from app.models.sales_task import SalesTask

            tid_task = str(args.get("task_id") or "")
            assignee = str(args.get("assignee") or "")
            norm = normalize_assignee(assignee)
            if not norm.get("ok"):
                return {"status": "failed", "error": norm.get("error")}
            t = db.query(SalesTask).filter(SalesTask.id == tid_task).first()
            if not t:
                return {"status": "failed", "error": "task_not_found"}
            gate = gate_agent_action(
                db,
                tenant_id=str(getattr(t, "tenant_id", "") or args.get("tenant_id") or ""),
                assignee=assignee,
                action="create_sales_task",
            )
            if not gate.get("ok"):
                return {"status": "failed", "error": gate.get("error"), "gate": gate}
            t.assigned_to = norm["id"]
            db.commit()
            record_agent_action(
                db,
                tenant_id=str(getattr(t, "tenant_id", "") or ""),
                agent_id=norm["id"],
                action="crm_sales_task_assign",
                target=str(t.id),
                payload=args,
                result={"assigned_to": t.assigned_to},
            )
            return {"status": "success", "task_id": str(t.id), "assigned_to": t.assigned_to}

        if name == "crm_pipeline_vocabulary":
            from app.services.deskcomm.pipeline_vocabulary import get_vocabulary, set_vocabulary

            tid = str(args.get("tenant_id") or "")
            if not tid:
                return {"status": "failed", "error": "tenant_id_required"}
            patch = args.get("patch")
            if patch:
                return {"status": "success", "vocabulary": set_vocabulary(db, tid, patch)}
            return {"status": "success", "vocabulary": get_vocabulary(db, tid)}

        return {"status": "failed", "error": f"unknown_tool:{name}"}
