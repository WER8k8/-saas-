# -*- coding: utf-8 -*-
"""TradeAiAgentExecutor 出站（outreach.*）能力诚实定级测试。

背景：auto_sender 等发送类技能在「未真实发出」时仍可能返回 success_count=0
的结果；执行器此前一律报 succeeded —— 属于软假成功。本组测试锁定：
真实发出才 succeeded；0 发出如实 failed/skipped/degraded，绝不伪造 sent。
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest

from app.schemas.hermes_orchestration import TaskNode
from app.services.hermes.executors.base import ExecutorContext
from app.services.hermes.executors.trade_ai_agent_executor import TradeAiAgentExecutor


class _FakeSkill:
    def __init__(self, name: str, result: dict):
        self.name = name
        self._result = result

    async def run(self, exec_ctx):  # noqa: ARG002
        return self._result


class _FakeOrch:
    def __init__(self, skills: dict[str, _FakeSkill]):
        self._skills = skills

    def list_workflows(self):
        return []

    def list_skills(self):
        return list(self._skills.values())


def _patch_adapter(monkeypatch, skills: dict[str, _FakeSkill]) -> None:
    from app.services import adapters
    from app.services.adapters import tradeai  # noqa: F401  确保子模块已加载

    monkeypatch.setattr(tradeai, "is_available", lambda: True)
    monkeypatch.setattr(tradeai, "tenant_orchestrator", lambda tid: _FakeOrch(skills))


async def _run(monkeypatch, skills, capability: str, params: dict) -> object:
    _patch_adapter(monkeypatch, skills)
    node = TaskNode(id="n1", executor="trade_ai_agent", capability=capability, input=params)
    ctx = ExecutorContext(db=None, tenant_id="t1", plan_id="")
    return await TradeAiAgentExecutor().run(node, context=ctx)


def test_outreach_send_zero_success_is_failed_not_succeeded(monkeypatch):
    """0 成功 1 失败 → 如实 failed，绝不 succeeded，不伪造 sent。"""
    skills = {
        "auto_sender": _FakeSkill(
            "auto_sender",
            {
                "results": [{"status": "failed", "error": "No customer ID", "message_id": None}],
                "success_count": 0,
                "failed_count": 1,
                "scheduled_count": 0,
            },
        ),
    }
    res = asyncio.run(
        _run(monkeypatch, skills, "outreach.whatsapp", {"customers": [{"id": None}]})
    )
    assert res.status == "failed"
    assert "未伪造 sent" in (res.error or "")
    assert res.output["sent"] is False


def test_outreach_send_no_recipients_is_skipped(monkeypatch):
    """无收件人/无发送动作 → skipped，不报 succeeded。"""
    skills = {
        "auto_sender": _FakeSkill(
            "auto_sender",
            {"results": [], "success_count": 0, "failed_count": 0, "scheduled_count": 0},
        ),
    }
    res = asyncio.run(_run(monkeypatch, skills, "outreach.whatsapp", {}))
    assert res.status == "skipped"
    assert "未伪造 sent" in (res.error or "")


def test_outreach_send_real_success_is_succeeded(monkeypatch):
    """真实发出（success_count>0）→ succeeded 且 sent=True。"""
    skills = {
        "auto_sender": _FakeSkill(
            "auto_sender",
            {
                "results": [{"status": "sent", "message_id": "m1"}],
                "success_count": 1,
                "failed_count": 0,
                "scheduled_count": 0,
            },
        ),
    }
    res = asyncio.run(_run(monkeypatch, skills, "outreach.whatsapp", {"customers": [{}]}))
    assert res.status == "succeeded"
    assert res.output["sent"] is True
    assert res.output["artifact_kind"] == "send"


def test_outreach_send_dry_run_is_degraded_not_succeeded(monkeypatch):
    """dry_run 演练即使逐条标 sent，顶层也必须 degraded（未真实发送）。"""
    skills = {
        "auto_sender": _FakeSkill(
            "auto_sender",
            {
                "results": [{"status": "sent"}],
                "success_count": 1,
                "failed_count": 0,
                "scheduled_count": 0,
                "dry_run": True,
            },
        ),
    }
    res = asyncio.run(_run(monkeypatch, skills, "outreach.whatsapp", {"customers": [{}]}))
    assert res.status == "degraded"
    assert "未真实发送" in (res.error or "")


def test_outreach_email_draft_is_succeeded_draft_not_sent(monkeypatch):
    """message_generator 产出话术草稿 → succeeded 但 artifact_kind=draft、sent=False。"""
    skills = {
        "message_generator": _FakeSkill(
            "message_generator",
            {"subject": "Partnership", "body": "Hi!", "variables_used": []},
        ),
    }
    res = asyncio.run(_run(monkeypatch, skills, "outreach.email", {"customer": {}}))
    assert res.status == "succeeded"
    assert res.output["sent"] is False
    assert res.output["artifact_kind"] == "draft"
