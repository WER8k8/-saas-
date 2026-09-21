# -*- coding: utf-8 -*-
"""GoodJobCrmExecutor D3 驱动层契约回归测试（不连真桥、不连真库）。

验证（批次 C）：
1. 目录驱动能力面：get_capabilities() 来自共享目录（45 family），含审批标记；
2. D3 任务包签名：5 字段 + payload.family/method/path，幂等键确定性；
3. 目录外 family / 目录外 op → failed（drift guard）；
4. 无桥令牌 → 干净失败（不静默假成功）；
5. dry_run：不连桥也能校验 op 命中目录（离线可测）。
"""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from app.schemas.hermes_orchestration import TaskNode
from app.services.hermes.executors.base import ExecutorContext
from app.services.hermes.executors import goodjob_crm_executor as gje


def _ctx() -> ExecutorContext:
    return ExecutorContext(db=MagicMock(), tenant_id="tenant-1", plan_id="plan-1")


def _node(cap, **inp) -> TaskNode:
    return TaskNode(id="n1", executor="goodjob_crm", capability=cap, depends_on=[], input=inp)


def test_catalog_drives_capability_surface():
    """能力面来自共享目录（45 family），不再是旧 mock 的 9 个。"""
    caps = gje.GoodJobCrmExecutor.get_capabilities()
    assert len(caps) >= 40, f"期望 ~45 个目录能力，实际 {len(caps)}"
    # 审批标记从目录带出
    assert caps["goodjob_crm.whatsapp"]["needs_approval"] is True
    assert caps["goodjob_crm.commission"]["needs_approval"] is True
    # 每个能力都带真实 operation 清单
    assert any(o.startswith("POST") for o in caps["goodjob_crm.deals"]["operations"])


def test_dry_run_rejects_op_not_in_catalog():
    """目录外 op → failed（drift guard，不静默成功）。"""
    ex = gje.GoodJobCrmExecutor(dry_run=True)
    # deals family 合法 op：POST /api/deals
    bad = ex.run(_node("goodjob_crm.deals", op="POST /api/deals"), _ctx())
    bad = asyncio.run(bad) if asyncio.iscoroutine(bad) else bad
    assert bad.status == "succeeded"
    assert bad.output["requires_approval"] is False
    # 非法 op：GET 一个不存在的路径
    res = asyncio.run(ex.run(_node("goodjob_crm.deals", op="GET /api/deals/nonexistent-op"), _ctx()))
    assert res.status == "failed"
    assert "op_not_in_catalog" in (res.error or "")


def test_unknown_family_skips():
    """目录外 family → skipped（planner 应改派；诚实列出可用 family，不静默成功）。"""
    ex = gje.GoodJobCrmExecutor(dry_run=True)
    res = asyncio.run(ex.run(_node("goodjob_crm.not_a_family"), _ctx()))
    assert res.status == "skipped"
    assert "not_a_family" in (res.error or "")


def test_task_package_is_five_field_d3():
    """签名的任务包必须是 5 字段 + payload.family/method/path（供 GoodJob 目录校验）。"""
    ex = gje.GoodJobCrmExecutor(dry_run=True)
    node = _node("goodjob_crm.whatsapp", op="POST /api/whatsapp/messages/{id}/translate", id="m1", text="hi")
    pkg = ex._build_task_package(node, _ctx(), "whatsapp", "POST /api/whatsapp/messages/{id}/translate")
    for f in ("tenant_id", "idempotency_key", "lease_ttl", "checkpoint", "budget", "task_type", "payload"):
        assert f in pkg, f"缺字段 {f}"
    assert pkg["task_type"] == "capability.invoke"
    assert pkg["payload"]["family"] == "whatsapp"
    assert pkg["payload"]["method"] == "POST"
    assert pkg["payload"]["path"] == "/api/whatsapp/messages/{id}/translate"
    assert pkg["tenant_id"] == "tenant-1"
    # 幂等键确定性
    key2 = ex._build_task_package(node, _ctx(), "whatsapp", "POST /api/whatsapp/messages/{id}/translate")["idempotency_key"]
    assert pkg["idempotency_key"] == key2


def test_no_token_fails_cleanly():
    """无桥令牌（非 dry_run）→ 干净失败，绝不假成功。"""
    ex = gje.GoodJobCrmExecutor(base_url="http://127.0.0.1:4188", token="", dry_run=False)
    res = asyncio.run(ex.run(_node("goodjob_crm.customers", op="POST /api/customers"), _ctx()))
    assert res.status == "failed"
    assert "UJ_BRIDGE_TOKEN_not_configured" in (res.error or "")


def test_post_and_poll_to_done(monkeypatch):
    """送达 + D3 轮询到 done → succeeded（mock requests，不连真桥）。"""
    ex = gje.GoodJobCrmExecutor(base_url="http://127.0.0.1:4188", token="tok", dry_run=False)

    post_resp = MagicMock(status_code=200, headers={"content-type": "application/json"})
    post_resp.json.return_value = {"requestId": "r1", "data": {"status": "accepted", "duplicate": False}}
    get_resp = MagicMock(status_code=200, headers={"content-type": "application/json"})
    get_resp.json.return_value = {"data": {"status": "done", "result_ref": "capability:inv_k"}}
    get_resp.raise_for_status.return_value = None

    import requests as _rq
    with patch.object(_rq, "post", return_value=post_resp), \
         patch.object(_rq, "get", return_value=get_resp), \
         patch.object(gje, "_POLL_INTERVAL", 0):
        res = asyncio.run(ex.run(_node("goodjob_crm.customers", op="POST /api/customers"), _ctx()))
    assert res.status == "succeeded"
    assert res.output["result_ref"] == "capability:inv_k"


def test_lease_expired_maps_to_redispatch(monkeypatch):
    """lease_expired（GoodJob 没接住 / 租约到期）→ failed，Hermes 可重派（D3）。"""
    ex = gje.GoodJobCrmExecutor(base_url="http://127.0.0.1:4188", token="tok", dry_run=False)
    post_resp = MagicMock(status_code=200, headers={"content-type": "application/json"})
    post_resp.json.return_value = {"data": {"status": "accepted"}}
    get_resp = MagicMock(status_code=404, headers={"content-type": "application/json"})
    get_resp.raise_for_status.return_value = None
    import requests as _rq
    with patch.object(_rq, "post", return_value=post_resp), \
         patch.object(_rq, "get", return_value=get_resp), \
         patch.object(gje, "_POLL_INTERVAL", 0), \
         patch.object(gje, "_MAX_POLLS", 1):
        res = asyncio.run(ex.run(_node("goodjob_crm.todos", op="POST /api/todos"), _ctx()))
    assert res.status == "failed"
    assert res.output.get("bridge_status") == "lease_expired"
