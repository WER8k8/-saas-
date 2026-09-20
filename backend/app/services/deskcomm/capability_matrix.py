# -*- coding: utf-8 -*-
"""Deskcomm × 优丁能力矩阵 — 智能取舍唯一真相源。

原则：重叠不引入第二实现；不重叠以能力/契约并入 UJ；不搬 Next/Supabase 运行时。
"""
from __future__ import annotations

from typing import Any, TypedDict


class CapabilityRow(TypedDict):
    id: str
    deskcomm: str
    overlap: str
    introduce: bool
    target: str
    note: str


CAPABILITY_MATRIX: tuple[CapabilityRow, ...] = (
    {
        "id": "crm_core",
        "deskcomm": "客户/联系人/商机/跟进基础 CRM",
        "overlap": "GoodJob + 优丁询盘/销售任务",
        "introduce": False,
        "target": "goodjob_function_domain",
        "note": "重叠：禁止平行第二套 CRM 表/UI",
    },
    {
        "id": "whatsapp_basic",
        "deskcomm": "WhatsApp 收发/会话 Inbox",
        "overlap": "GoodJob whatsapp-plugin + TradeAI",
        "introduce": False,
        "target": "existing_adapters",
        "note": "重叠：不引入 WAHA 第二栈作主通道",
    },
    {
        "id": "auth_multitenant",
        "deskcomm": "Supabase Auth + 自托管安装器",
        "overlap": "优丁唯一 /login + 部署脚本",
        "introduce": False,
        "target": "uj_login_lock",
        "note": "LOGIN-LOCK：禁止第二登录",
    },
    {
        "id": "nuvemshop",
        "deskcomm": "Nuvemshop 巴西电商集成",
        "overlap": "非优丁主链",
        "introduce": False,
        "target": "out_of_scope",
        "note": "舍：非建材外贸主叙事",
    },
    {
        "id": "mcp_crm_tools",
        "deskcomm": "MCP 暴露 CRM 操作 tools",
        "overlap": "优丁仅有 hermes_orchestrate 单工具",
        "introduce": True,
        "target": "deskcomm.crm_sales_os_tools",
        "note": "并入：询盘/任务/跟进/词汇工具，操作 UJ PG",
    },
    {
        "id": "agent_assignee",
        "deskcomm": "AI Agent 一等 assignee + 治理",
        "overlap": "无完整等价物",
        "introduce": True,
        "target": "deskcomm.agent_assignee",
        "note": "并入：agent:* 指派 + 预算闸 + 审计",
    },
    {
        "id": "automation_when_if_then",
        "deskcomm": "QUANDO/SE/ENTÃO 自动化",
        "overlap": "Hermes 有任务面，无轻量规则层",
        "introduce": True,
        "target": "deskcomm.automation_rules",
        "note": "并入：规则评估 → 销售任务/hermes 意图",
    },
    {
        "id": "pipeline_vocabulary",
        "deskcomm": "多行业 pipeline 词汇配置",
        "overlap": "管道阶段硬编码倾向",
        "introduce": True,
        "target": "deskcomm.pipeline_vocabulary",
        "note": "并入：租户可覆盖 lead/won 标签",
    },
    {
        "id": "rag_flywheel",
        "deskcomm": "已解决会话回流 RAG",
        "overlap": "UJ knowledge_queue 存在",
        "introduce": True,
        "target": "knowledge_queue_hook",
        "note": "部分重叠：只加钩子，不建第二知识库",
    },
    {
        "id": "stop_handoff",
        "deskcomm": "STOP/退订 → 人接手",
        "overlap": "触达路径缺口",
        "introduce": True,
        "target": "deskcomm.stop_handoff",
        "note": "并入：检测后 handoff，禁止自动再发",
    },
    {
        "id": "tenant_ai_budget",
        "deskcomm": "租户 AI budget",
        "overlap": "ai_usage 有计量",
        "introduce": True,
        "target": "agent_assignee.budget",
        "note": "并入闸门：Agent 动作前检查",
    },
    {
        "id": "lgpd_full",
        "deskcomm": "LGPD redact/export 全流程",
        "overlap": "UJ 有审计片段",
        "introduce": False,
        "target": "phase1_audit_only",
        "note": "P1：本轮只保证 Agent 动作可审计",
    },
    {
        "id": "kanban_fractional",
        "deskcomm": "分数索引 Kanban",
        "overlap": "销售看板已有简化版",
        "introduce": False,
        "target": "phase2_ui",
        "note": "P2：规格登记，本轮不做 UI 重写",
    },
    {
        "id": "waha_antiban_multinum",
        "deskcomm": "多号反封运营",
        "overlap": "性能/运营风险高",
        "introduce": False,
        "target": "phase2_ops",
        "note": "P2：智能取舍—暂不并，避免误封生产号",
    },
)


def introduced_capabilities() -> list[str]:
    return [r["id"] for r in CAPABILITY_MATRIX if r["introduce"]]


def skipped_capabilities() -> list[str]:
    return [r["id"] for r in CAPABILITY_MATRIX if not r["introduce"]]


def matrix_report() -> dict[str, Any]:
    return {
        "source": "deskcomm_capability_matrix_v1",
        "principle": [
            "重叠不引入第二实现",
            "不重叠以能力契约并入 UJ/Hermes",
            "不搬 Next/Supabase/第二登录",
            "无 Key 诚实降级",
        ],
        "introduce_count": len(introduced_capabilities()),
        "skip_count": len(skipped_capabilities()),
        "rows": list(CAPABILITY_MATRIX),
        "introduced": introduced_capabilities(),
        "skipped": skipped_capabilities(),
    }
