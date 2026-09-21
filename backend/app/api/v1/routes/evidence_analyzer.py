# -*- coding: utf-8 -*-
# Copyright (c) 2026 吕博旺 (131025199403304817). All rights reserved.
"""Browser 证据自动分析管道 API。"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, Query

from app.core.database import get_db
from app.core.security import get_current_user
from app.services.browser_runtime.evidence_analyzer import evidence_analyzer
from app.services.browser_runtime.evidence import EvidenceRecord, persist_evidence

ROUTE_PREFIX = ""
router = APIRouter(prefix="/evidence", tags=["Browser证据分析"])


@router.post("/analyze")
async def analyze_evidence_payload(
    payload: dict = Body(...),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """分析单条或批量 EvidenceRecord 载荷，并发布事件。"""
    items = payload.get("evidences") or payload.get("items") or payload.get("evidence")
    if items is None and payload.get("id"):
        items = [payload]
    if items is None:
        items = []
    if isinstance(items, dict):
        items = [items]
    tenant_id = str(payload.get("tenant_id") or getattr(user, "tenant_id", "") or "")
    result = evidence_analyzer.analyze_and_emit(items, tenant_id=tenant_id, source="api")
    return {"code": 0, "data": result}


@router.post("/analyze/persisted")
async def analyze_and_persist(
    payload: dict = Body(...),
    db=Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """落库一条证据后再分析（打通 persist → analyze 管道）。"""
    data = payload.get("evidence") or payload
    if not isinstance(data, dict):
        raise ValueError("evidence must be object")
    record = EvidenceRecord(
        tenant_id=str(data.get("tenant_id") or getattr(user, "tenant_id", "") or None),
        actor=str(data.get("actor") or "api"),
        action=str(data.get("action") or ""),
        target_url=data.get("target_url"),
        status=str(data.get("status") or "success"),
        input_summary=data.get("input_summary"),
        output_summary=data.get("output_summary"),
        screenshot_path=data.get("screenshot_path"),
        fill_selector=data.get("fill_selector"),
        fill_value_sanitized=data.get("fill_value_sanitized"),
        fill_value_original_len=int(data.get("fill_value_original_len") or 0),
        click_target=data.get("click_target"),
        submit_approval_id=data.get("submit_approval_id"),
        submit_auto=bool(data.get("submit_auto") or False),
        error_code=data.get("error_code"),
        error_message=data.get("error_message"),
        policy_verdict=data.get("policy_verdict"),
        metadata=dict(data.get("metadata") or {}),
    )
    # 若调用方直接给了终态时间字段，按 status 标记
    st = str(data.get("status") or record.status).lower()
    if st == "failed":
        record.mark_failed(error_code=record.error_code, error_message=record.error_message or "")
    elif st == "blocked" and record.policy_verdict:
        record.mark_blocked(policy_verdict=record.policy_verdict)
    elif st == "degraded":
        record.mark_degraded(error_message=record.error_message or "")
    else:
        record.mark_success(
            output_summary=record.output_summary,
            screenshot_path=record.screenshot_path,
            fill_selector=record.fill_selector,
            fill_value_sanitized=record.fill_value_sanitized,
            fill_value_original_len=record.fill_value_original_len,
            click_target=record.click_target,
            submit_approval_id=record.submit_approval_id,
            submit_auto=record.submit_auto,
        )

    persist_result = persist_evidence(record, task_id=data.get("task_id"), db=db)
    analysis = evidence_analyzer.analyze_and_emit(
        record,
        tenant_id=str(record.tenant_id or ""),
        source="api_persist_analyze",
    )
    return {
        "code": 0,
        "data": {
            "evidence_id": record.id,
            "persisted": persist_result,
            "analysis": analysis,
        },
    }


@router.post("/analyze/jsonl")
async def analyze_jsonl(
    tenant_id: str = Query(default="global"),
    limit: int = Query(default=200, ge=1, le=2000),
    base_dir: Optional[str] = Query(default=None),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """分析落盘 audit.jsonl 中的最近证据。"""
    result = evidence_analyzer.analyze_from_jsonl(
        tenant_id=tenant_id or "global",
        limit=limit,
        base_dir=base_dir,
    )
    return {"code": 0, "data": result}


@router.get("/analyzer/stats")
async def analyzer_health(user=Depends(get_current_user)) -> dict[str, Any]:
    """分析器配置与健康信息。"""
    return {
        "code": 0,
        "data": {
            "slow_ms": evidence_analyzer.slow_ms,
            "write_actions": sorted(evidence_analyzer.write_actions),
            "sensitive_actions": sorted(evidence_analyzer.sensitive_actions),
            "emit_events": evidence_analyzer.emit_events,
        },
    }
