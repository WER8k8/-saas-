# -*- coding: utf-8 -*-
"""Deskcomm 不重叠能力并入 — 矩阵/STOP/预算/自动化/词汇。"""
from __future__ import annotations

from app.services.deskcomm.capability_matrix import (
    introduced_capabilities,
    matrix_report,
    skipped_capabilities,
)
from app.services.deskcomm.stop_handoff import detect_stop
from app.services.deskcomm.agent_assignee import (
    ALLOWED_OFFLINE_AGENT_ACTIONS,
    normalize_assignee,
    gate_agent_action,
)
from app.services.deskcomm.automation_rules import evaluate_event, upsert_rule, list_rules
from app.services.deskcomm.pipeline_vocabulary import DEFAULT_VOCABULARY, get_vocabulary


def test_matrix_skips_overlapping_and_introduces_unique():
    report = matrix_report()
    intro = set(introduced_capabilities())
    skip = set(skipped_capabilities())
    # 重叠不引入
    for cid in ("crm_core", "whatsapp_basic", "auth_multitenant", "nuvemshop"):
        assert cid in skip, cid
        assert cid not in intro
    # 不重叠并入
    for cid in ("mcp_crm_tools", "agent_assignee", "automation_when_if_then", "stop_handoff", "pipeline_vocabulary"):
        assert cid in intro, cid
    assert report["introduce_count"] >= 5
    assert "LOGIN-LOCK" in str(report) or any("唯一" in p or "/login" in p for p in report["principle"])


def test_stop_handoff_never_fake_send():
    r1 = detect_stop("please STOP messaging me")
    assert r1["stop"] is True and r1["handoff"] is True and r1["sent"] is False
    r2 = detect_stop("退订")
    assert r2["stop"] is True and r2["sent"] is False
    r3 = detect_stop("请问岩棉价格")
    assert r3["stop"] is False and r3["handoff"] is False


def test_normalize_assignee_and_agent_action_allowlist():
    a = normalize_assignee("agent:wa-bot")
    assert a["ok"] and a["kind"] == "agent"
    u = normalize_assignee("user:tenant-admin")
    assert u["ok"] and u["kind"] == "user"
    assert "create_sales_task" in ALLOWED_OFFLINE_AGENT_ACTIONS
    # 外发类不在离线白名单
    assert "whatsapp_send" not in ALLOWED_OFFLINE_AGENT_ACTIONS


def test_gate_rejects_agent_when_action_not_allowed():
    class _DB:
        pass

    g = gate_agent_action(_DB(), tenant_id="t1", assignee="agent:x", action="whatsapp_send")
    assert g["ok"] is False
    assert g.get("stage") in ("action_allowlist", "budget", "assignee")


def test_automation_rule_dry_run_handoff():
    upsert_rule(
        "tenant-demo",
        {
            "id": "r-stop",
            "name": "stop to handoff",
            "when": "message.stop",
            "if": {},
            "then": {"action": "handoff"},
            "enabled": True,
        },
    )
    assert len(list_rules("tenant-demo")) >= 1

    class _DB:
        pass

    out = evaluate_event(
        _DB(),
        "tenant-demo",
        {"when": "message.stop", "payload": {"text": "STOP"}},
        dry_run=True,
    )
    assert out["matched"] >= 1
    hit = out["hits"][0]
    assert hit["action"] == "handoff"
    assert hit["result"].get("sent") is False


def test_pipeline_vocabulary_default_building_materials():
    class _DB:
        pass

    v = get_vocabulary(_DB(), "no-such-tenant")
    assert v["won_label"] == DEFAULT_VOCABULARY["won_label"]
    assert v["source"] == "default_building_materials"


def test_hermes_mcp_manifest_includes_crm_tools():
    from app.services.hermes.hermes_mcp_server import HermesMCPServer

    names = {t["name"] for t in HermesMCPServer.get_tool_manifest()}
    assert "hermes_orchestrate" in names
    assert "crm_capability_matrix" in names
    assert "crm_stop_check" in names
