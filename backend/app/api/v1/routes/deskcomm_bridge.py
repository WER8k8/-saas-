# -*- coding: utf-8 -*-
"""Deskcomm 不重叠能力并入桥 — 矩阵 / CRM MCP / 自动化 / 词汇 / STOP。"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.response import error_response, success_response
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User

ROUTE_PREFIX = "/deskcomm-bridge"
ROUTE_TAGS = ["Deskcomm能力并入"]

router = APIRouter(tags=["Deskcomm能力并入"])


@router.get("/matrix")
def get_capability_matrix(current_user: User = Depends(get_current_user)):
    """Deskcomm×优丁取舍矩阵（重叠不引入 / 不重叠并入）。"""
    from app.services.deskcomm.capability_matrix import matrix_report

    return success_response(data=matrix_report())


@router.get("/mcp/tools")
def list_crm_mcp_tools(current_user: User = Depends(get_current_user)):
    """CRM Sales-OS MCP 工具清单（操作优丁，非 Deskcomm 运行时）。"""
    from app.services.deskcomm.crm_sales_os_tools import CrmSalesOsTools

    return success_response(data={"tools": CrmSalesOsTools.get_tool_manifest()})


@router.post("/mcp/call")
async def call_crm_mcp(
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    name = str(body.get("tool") or body.get("name") or "")
    args = body.get("arguments") or body.get("params") or {}
    if not name:
        return error_response(400, "tool_required")
    from app.services.deskcomm.crm_sales_os_tools import CrmSalesOsTools

    result = await CrmSalesOsTools.call_tool(name, args, db=db)
    return success_response(data=result)


class AutomationRuleIn(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    when: str
    if_: Optional[dict] = Field(default=None, alias="if")
    then: dict
    enabled: bool = True

    model_config = {"populate_by_name": True}


@router.get("/automation/rules")
def list_automation_rules(
    tenant_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tid = tenant_id or str(getattr(current_user, "tenant_id", "") or "")
    if not tid:
        return error_response(400, "tenant_id_required")
    from app.services.deskcomm.automation_rules import list_rules

    return success_response(data={"tenant_id": tid, "items": list_rules(tid)})


@router.post("/automation/rules")
def upsert_automation_rule(
    body: AutomationRuleIn,
    tenant_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tid = tenant_id or str(getattr(current_user, "tenant_id", "") or "")
    if not tid:
        return error_response(400, "tenant_id_required")
    from app.services.deskcomm.automation_rules import upsert_rule

    try:
        rule = upsert_rule(
            tid,
            {
                "id": body.id,
                "name": body.name,
                "when": body.when,
                "if": body.if_ or {},
                "then": body.then,
                "enabled": body.enabled,
            },
        )
    except ValueError as exc:
        return error_response(400, str(exc))
    return success_response(data=rule, message="automation rule saved")


@router.delete("/automation/rules/{rule_id}")
def delete_automation_rule(
    rule_id: str,
    tenant_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tid = tenant_id or str(getattr(current_user, "tenant_id", "") or "")
    from app.services.deskcomm.automation_rules import delete_rule

    ok = delete_rule(tid, rule_id)
    return success_response(data={"deleted": ok})


class AutomationEventIn(BaseModel):
    when: str
    payload: dict = Field(default_factory=dict)
    dry_run: bool = False
    tenant_id: Optional[str] = None


@router.post("/automation/evaluate")
def evaluate_automation(
    body: AutomationEventIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tid = body.tenant_id or str(getattr(current_user, "tenant_id", "") or "")
    if not tid:
        return error_response(400, "tenant_id_required")
    from app.services.deskcomm.automation_rules import evaluate_event

    return success_response(
        data=evaluate_event(db, tid, {"when": body.when, "payload": body.payload}, dry_run=body.dry_run)
    )


@router.get("/pipeline/vocabulary")
def get_pipeline_vocab(
    tenant_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tid = tenant_id or str(getattr(current_user, "tenant_id", "") or "")
    if not tid:
        return error_response(400, "tenant_id_required")
    from app.services.deskcomm.pipeline_vocabulary import get_vocabulary

    return success_response(data=get_vocabulary(db, tid))


class VocabPatch(BaseModel):
    patch: dict
    tenant_id: Optional[str] = None


@router.post("/pipeline/vocabulary")
def set_pipeline_vocab(
    body: VocabPatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tid = body.tenant_id or str(getattr(current_user, "tenant_id", "") or "")
    if not tid:
        return error_response(400, "tenant_id_required")
    from app.services.deskcomm.pipeline_vocabulary import set_vocabulary

    try:
        return success_response(data=set_vocabulary(db, tid, body.patch))
    except ValueError as exc:
        return error_response(400, str(exc))


class StopCheckIn(BaseModel):
    text: str


@router.post("/stop-check")
def stop_check(body: StopCheckIn, current_user: User = Depends(get_current_user)):
    """STOP/退订检测：handoff=true 且 sent=false（禁止假外发）。"""
    from app.services.deskcomm.stop_handoff import detect_stop

    return success_response(data=detect_stop(body.text))
