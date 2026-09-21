# -*- coding: utf-8 -*-
"""runtime.execute_plugin 对 catalog 中全部 kind 的分发完整性测试。

覆盖 visual_studio 分支（feature flag 未启用 → not_ready 诚实降级）等。
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest

from app.services.hermes.runtime import execute_plugin, _execute_visual_studio


def _spec(**over):
    spec = {
        "id": "visual_studio_instatic",
        "public": {"name": "Instatic 可视化精修"},
        "internal": {"kind": "visual_studio", "handler": "visual_studio_instatic_v1"},
    }
    spec.update(over)
    return spec


def _make_tenant(db):
    from app.models.tenant import Tenant, TenantPlan

    plan = TenantPlan(name="Free Plan", code="free_kinds", price_monthly=0, price_yearly=0)
    db.add(plan)
    db.flush()
    tenant = Tenant(name="Kinds Tenant", domain="kinds-test.example.com", plan_id=plan.id)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return str(tenant.id)


def test_visual_studio_dispatch_returns_not_ready(db_session, monkeypatch):
    """execute_plugin 识别 visual_studio kind 走对应分支，flag 关 → 诚实降级 not_ready。"""
    monkeypatch.delenv("FF_INSTATIC_STUDIO", raising=False)
    monkeypatch.setenv("HERMES_AGENCY_LLM_ENABLED", "false")

    tenant_id = _make_tenant(db_session)
    from app.services.hermes.install_service import install_plugin
    install_plugin(db_session, tenant_id=tenant_id, plugin_id="visual_studio_instatic", enabled=True)
    res = execute_plugin(
        db_session, tenant_id=tenant_id, plugin_id="visual_studio_instatic", message="生成静态站点",
        context={"product_name": "岩棉板"},
    )
    assert res["handler_kind"] == "visual_studio"
    assert res["tool_result"]["status"] == "not_ready"
    assert "未产生任何建站产物" in res["reply"]


def test_visual_studio_flag_off_returns_not_ready(monkeypatch):
    """feature flag 未启用 → 如实降级 not_ready，不虚构产物。"""
    monkeypatch.delenv("FF_INSTATIC_STUDIO", raising=False)

    class FakeSettings:
        FF_INSTATIC_STUDIO = False

    monkeypatch.setattr("app.core.config.settings", FakeSettings())
    res = _execute_visual_studio(
        None, plugin_id="visual_studio_instatic", spec=_spec(), kind="visual_studio",
        handler="visual_studio_instatic_v1", message="生成静态站点", tenant_id="t1", ctx={},
    )
    assert res["tool_result"]["status"] == "not_ready"
    assert "未产生任何建站产物" in res["reply"]


def test_visual_studio_flag_on_returns_ready(monkeypatch):
    """feature flag 启用 → 驱动精修种子生成并 ready，不再 not_ready。"""
    monkeypatch.delenv("FF_INSTATIC_STUDIO", raising=False)

    class FakeSettings:
        FF_INSTATIC_STUDIO = True

    monkeypatch.setattr("app.core.config.settings", FakeSettings())
    seed = {
        "artifact": {
            "template_id": "premium-b2b-v1",
            "product_name": "岩棉板",
            "saved": True,
            "seed_source": "template",
            "publish_ready": False,
            "l_pro_publish_gate": {"ok": False, "publish_ready": False},
        },
        "skills_applied": ["premium-b2b-v1"],
    }
    monkeypatch.setattr("app.services.hermes.runtime._build_instatic_seed", lambda *a, **k: seed)
    res = _execute_visual_studio(
        None, plugin_id="visual_studio_instatic", spec=_spec(), kind="visual_studio",
        handler="visual_studio_instatic_v1", message="生成静态站点", tenant_id="t1", ctx={},
    )
    assert res["tool_result"]["status"] == "ready"
    assert res["tool_result"]["seed"]["template_id"] == "premium-b2b-v1"
    assert "精修种子已生成并保存" in res["reply"]


def test_visual_studio_seed_failed_fail_closed(monkeypatch):
    """flag 启用但种子生成失败 → fail-closed not_ready，不宣称已精修。"""
    monkeypatch.delenv("FF_INSTATIC_STUDIO", raising=False)

    class FakeSettings:
        FF_INSTATIC_STUDIO = True

    monkeypatch.setattr("app.core.config.settings", FakeSettings())
    monkeypatch.setattr("app.services.hermes.runtime._build_instatic_seed", lambda *a, **k: None)
    res = _execute_visual_studio(
        None, plugin_id="visual_studio_instatic", spec=_spec(), kind="visual_studio",
        handler="visual_studio_instatic_v1", message="", tenant_id="t1", ctx={},
    )
    assert res["tool_result"]["status"] == "not_ready"
    assert res["tool_result"]["reason"] == "instatic_seed_failed"
    assert "未产生任何建站/精修产物" in res["reply"]
