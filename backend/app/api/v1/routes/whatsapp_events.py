# -*- coding: utf-8 -*-
# Copyright (c) 2026 吕博旺 (131025199403304817). All rights reserved.
"""WhatsApp 入站事件总线路由 — Plugin @3100 → 核心后端实时同步。

端点：
- POST /api/v1/whatsapp-events/inbound   入站消息
- POST /api/v1/whatsapp-events/ack       消息回执/失败
- POST /api/v1/whatsapp-events/connection 连接状态
- GET  /api/v1/whatsapp-events/stats     总线统计
- GET  /api/v1/whatsapp-events/recent    最近入站（内存窗口）
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query

from app.core.database import get_db
from app.services.whatsapp_event_bus import (
    verify_inbound_token,
    whatsapp_inbound_event_bus,
)

ROUTE_PREFIX = ""
router = APIRouter(prefix="/whatsapp-events", tags=["WhatsApp入站事件总线"])


def _require_token(x_whatsapp_token: Optional[str] = Header(default=None)) -> None:
    if not verify_inbound_token(x_whatsapp_token):
        raise HTTPException(status_code=401, detail="invalid WhatsApp inbound token")


@router.post("/inbound")
async def whatsapp_inbound(
    payload: dict = Body(...),
    db=Depends(get_db),
    persist: bool = Query(default=True),
    _auth: None = Depends(_require_token),
) -> dict[str, Any]:
    """接收 WhatsApp Plugin 入站消息，落库（可选）并发布事件总线。"""
    result = whatsapp_inbound_event_bus.publish_inbound(payload or {}, db=db, persist=persist)
    return {"code": 0 if result.get("accepted") else 400, "data": result}


@router.post("/ack")
async def whatsapp_ack(
    payload: dict = Body(...),
    _auth: None = Depends(_require_token),
) -> dict[str, Any]:
    """消息回执：delivered/read/failed。"""
    phone = str(payload.get("phone") or payload.get("from") or "")
    if not phone:
        raise HTTPException(status_code=400, detail="phone required")
    result = whatsapp_inbound_event_bus.publish_ack(
        phone=phone,
        msg_id=str(payload.get("msg_id") or payload.get("message_id") or ""),
        ack_type=str(payload.get("ack_type") or payload.get("status") or "delivered"),
        tenant_id=str(payload.get("tenant_id") or ""),
        payload_extra={k: v for k, v in payload.items() if k not in {"phone", "from", "msg_id", "message_id", "ack_type", "status", "tenant_id"}},
    )
    return {"code": 0, "data": result}


@router.post("/connection")
async def whatsapp_connection(
    payload: dict = Body(...),
    _auth: None = Depends(_require_token),
) -> dict[str, Any]:
    """WhatsApp 连接状态变化。"""
    state = str(payload.get("state") or payload.get("status") or "unknown")
    result = whatsapp_inbound_event_bus.publish_connection_state(
        state=state,
        account_id=str(payload.get("account_id") or payload.get("accountId") or ""),
        tenant_id=str(payload.get("tenant_id") or ""),
        detail=str(payload.get("detail") or payload.get("message") or ""),
    )
    return {"code": 0, "data": result}


@router.get("/stats")
async def whatsapp_bus_stats(_auth: None = Depends(_require_token)) -> dict[str, Any]:
    """入站事件总线统计。"""
    return {"code": 0, "data": whatsapp_inbound_event_bus.stats}


@router.get("/recent")
async def whatsapp_bus_recent(
    limit: int = Query(default=20, ge=1, le=200),
    _auth: None = Depends(_require_token),
) -> dict[str, Any]:
    """最近入站事件（内存窗口，运维观测用）。"""
    return {"code": 0, "data": whatsapp_inbound_event_bus.recent(limit=limit)}
