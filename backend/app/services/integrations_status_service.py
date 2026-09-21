# -*- coding: utf-8 -*-
# Copyright (c) 2026 吕博旺 (131025199403304817). All rights reserved.
"""双栈集成状态 — FastAPI 主库 + SEO 矩阵 + 可选 Node seo-backend。

每项返回：value + level(ok|warn|bad|info|skip) + label + hint（好坏说明）。
"""

from __future__ import annotations

import os

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings


def _collect_route_paths(app) -> list[str]:
    """尽量收集真实已挂载路径（openapi 优先，再回退 app.routes / 聚合 router）。"""
    paths: list[str] = []
    seen: set[str] = set()

    def _add(p: str) -> None:
        p = (p or "").strip()
        if p and p not in seen:
            seen.add(p)
            paths.append(p)

    # 1) openapi（强制刷新缓存，避免陈旧 schema）
    try:
        if hasattr(app, "openapi_schema"):
            app.openapi_schema = None
        schema = app.openapi() or {}
        for p in (schema.get("paths") or {}).keys():
            _add(str(p))
    except Exception:
        pass

    # 2) app.routes
    try:
        for r in app.routes:
            _add(str(getattr(r, "path", "") or ""))
    except Exception:
        pass

    # 3) 聚合 router / v1 router（解决 include_router 时序导致 app.routes 偏少）
    try:
        from app.api import router as api_router
        for r in getattr(api_router, "routes", []) or []:
            p = str(getattr(r, "path", "") or "")
            if p.startswith("/api"):
                _add(p)
            elif p.startswith("/v1"):
                _add(f"/api{p}")
            elif p.startswith("/"):
                _add(f"/api/v1{p}" if not p.startswith("/api") else p)
    except Exception:
        pass
    try:
        from app.api.v1.routes import router as v1_router
        for r in getattr(v1_router, "routes", []) or []:
            p = str(getattr(r, "path", "") or "")
            if p.startswith("/api"):
                _add(p)
            elif p.startswith("/v1"):
                _add(f"/api{p}")
            elif p.startswith("/"):
                # v1 子路由常为 /seo-matrix/... 挂载后为 /api/v1/seo-matrix/...
                _add(f"/api/v1{p}")
    except Exception:
        pass

    return paths


def _count_route_prefix(app, prefix: str) -> int:
    """按前缀统计已挂载路由（用合并后的路径集合）。"""
    prefix = (prefix or "").rstrip("/") + "/" if prefix and not prefix.endswith("/") else prefix
    count = 0
    for p in _collect_route_paths(app):
        if not prefix:
            continue
        if p == prefix.rstrip("/") or p.startswith(prefix):
            count += 1
    return count


def _count_prefix_in_paths(paths: list[str], prefix: str) -> int:
    if not prefix:
        return 0
    pfx = prefix if prefix.endswith("/") else prefix + "/"
    bare = prefix.rstrip("/")
    return sum(1 for p in paths if p == bare or p.startswith(pfx))


def _route_health(count: int, kind: str) -> dict:
    """路由数量好坏：0=异常未挂载；少量=偏少；正常=可用。"""
    if count <= 0:
        return {
            "level": "bad",
            "label": "异常",
            "hint": f"{kind} 路由数为 0：模块可能未挂载到 FastAPI，SEO 能力入口不可用。检查 routes/__init__.py 是否 include 了对应 router。",
        }
    if count < 5:
        return {
            "level": "warn",
            "label": "偏少",
            "hint": f"{kind} 仅 {count} 条路由，功能可能不完整，请确认子路由是否遗漏。",
        }
    return {
        "level": "ok",
        "label": "正常",
        "hint": f"{kind} 已挂载 {count} 条路由，入口可用。",
    }


def _seo_backend_health(status: str, url: str, detail: str | None) -> dict:
    if status == "connected":
        return {
            "level": "ok",
            "label": "正常",
            "hint": f"Node seo-backend 已连通（{url}）" + (f"：{detail}" if detail else "") + "。可经 super-admin/seo-proxy 使用历史矩阵能力。",
        }
    if status == "degraded":
        return {
            "level": "warn",
            "label": "降级",
            "hint": f"seo-backend 有响应但异常（{url}）" + (f"：{detail}" if detail else "") + "。历史矩阵功能可能不稳定。",
        }
    if status == "unreachable":
        return {
            "level": "bad",
            "label": "不可达",
            "hint": f"seo-backend 配置了地址但无法访问（{url}）" + (f"：{detail}" if detail else "") + "。请确认 Node 进程已启动、端口正确，或清空 SEO_BACKEND_URL 改为可选关闭。",
        }
    # not_configured
    return {
        "level": "info",
        "label": "未启用",
        "hint": (
            f"当前 SEO_BACKEND_URL 仍为占位 {url} 或未单独配置，系统按「可选旁路」处理。"
            " 新能力请走 FastAPI /api/v1/seo-matrix 与 /api/v1/seo/*；"
            "若要启用历史 Node 矩阵，请设置 SEO_BACKEND_URL（本机常见为 http://localhost:3001，注意勿与官网 :3000 冲突）后点刷新。"
        ),
    }


def _primary_health(primary: str) -> dict:
    return {
        "level": "ok",
        "label": "运行中",
        "hint": f"主栈为 {primary}，本接口能返回数据即表示进程与路由层已响应。",
    }


def _build_acquisition_api_panel() -> dict:
    """获客渠道 API 配置状态面板"""
    ga4_configured = bool(os.getenv("NUXT_PUBLIC_GA4_MEASUREMENT_ID", ""))
    google_cse_configured = bool(settings.GOOGLE_CSE_API_KEY and settings.GOOGLE_CSE_CX)
    whatsapp_configured = bool(
        settings.WHATSAPP_ACCESS_TOKEN and settings.WHATSAPP_PHONE_NUMBER_ID
    )
    total = 3
    configured = sum([ga4_configured, google_cse_configured, whatsapp_configured])
    modules = [
        {
            "id": "ga4",
            "name": "Google Analytics 4",
            "status": "configured" if ga4_configured else "pending",
            "hint": "网站流量分析，判断哪个渠道来的访客有价值",
            "env_key": "NUXT_PUBLIC_GA4_MEASUREMENT_ID",
            "doc_link": "https://support.google.com/analytics/answer/9304153",
            "category": "流量分析",
        },
        {
            "id": "google_cse",
            "name": "Google Custom Search API",
            "status": "configured" if google_cse_configured else "pending",
            "hint": "Google 搜索获客，替换 Mock 用真实搜索结果开发客户",
            "env_key": "GOOGLE_CSE_API_KEY + GOOGLE_CSE_CX",
            "doc_link": "https://developers.google.com/custom-search/v1/introduction",
            "category": "获客搜索",
        },
        {
            "id": "whatsapp",
            "name": "WhatsApp Business Cloud API",
            "status": "configured" if whatsapp_configured else "pending",
            "hint": "WhatsApp 开发信发送，打开率 >90% 的外贸触达渠道",
            "env_key": "WHATSAPP_ACCESS_TOKEN + WHATSAPP_PHONE_NUMBER_ID",
            "doc_link": "https://developers.facebook.com/docs/whatsapp/cloud-api",
            "category": "消息触达",
        },
    ]
    status_label = "未开始"
    status_level = "bad"
    if configured == total:
        status_label = "全部就绪"
        status_level = "ok"
    elif configured > 0:
        status_label = "部分配置"
        status_level = "warn"

    overall_hint = (
        f"获客渠道 API {configured}/{total} 已配置。"
        + ("可以开始用真实数据判断渠道投入了！" if configured == total
           else "建议优先配置 Google CSE + WhatsApp，跑第一批真实客户线索。")
    )
    usage_tips = [
        "配置好 GA4 后，观察 1-2 周流量数据，看哪些国家/关键词带来的访客有询盘",
        "Google CSE 每天免费 100 次查询，建议先跑 3-5 个核心关键词测试线索质量",
        "WhatsApp 先从高意向客户发模板消息破冰，不要上来就群发，避免封号",
        "三个都配好后，可以跑 A/B 测试：邮件 vs WhatsApp 哪个回复率高",
    ]
    return {
        "id": "acquisition_apis",
        "name": "获客渠道 API 配置",
        "total": total,
        "configured": configured,
        "status_label": status_label,
        "status_level": status_level,
        "overall_hint": overall_hint,
        "modules": modules,
        "usage_tips": usage_tips,
    }


def build_integrations_status(db: Session | None = None) -> dict:
    """构建集成栈状态 + 好坏判定。"""
    from app.main import app
    # 默认改为 3001：3000 本机常被官网占用；仍可用环境变量覆盖
    seo_backend_url = os.getenv("SEO_BACKEND_URL", "http://localhost:3001").rstrip("/")
    matrix_prefix = f"{settings.API_V1_PREFIX}/seo-matrix"
    advanced_prefix = f"{settings.API_V1_PREFIX}/seo"
    node_status = "not_configured"
    node_detail = None
    placeholder = seo_backend_url in {"http://localhost:3000", "http://127.0.0.1:3000"}
    if seo_backend_url and not placeholder:
        try:
            with httpx.Client(timeout=3) as client:
                resp = client.get(f"{seo_backend_url}/health")
                if resp.status_code >= 400:
                    resp = client.get(f"{seo_backend_url}/api/v1/health")
                node_status = "connected" if resp.status_code == 200 else "degraded"
                node_detail = f"HTTP {resp.status_code}"
        except Exception as exc:
            node_status = "unreachable"
            node_detail = str(exc)[:200]
    elif placeholder:
        node_status = "not_configured"
        node_detail = "占位地址（疑似误配 :3000 官网端口），未探测"

    all_paths = _collect_route_paths(app)
    matrix_count = _count_prefix_in_paths(all_paths, matrix_prefix)
    advanced_count = _count_prefix_in_paths(all_paths, advanced_prefix)
    total_api = sum(1 for p in all_paths if p.startswith("/api"))

    primary = "fastapi"
    matrix_h = _route_health(matrix_count, "SEO 矩阵")
    advanced_h = _route_health(advanced_count, "高级 SEO")
    node_h = _seo_backend_health(node_status, seo_backend_url, node_detail)
    primary_h = _primary_health(primary)

    levels = [primary_h["level"], matrix_h["level"], advanced_h["level"], node_h["level"]]
    if "bad" in levels:
        overall = {"level": "bad", "label": "有阻断项", "hint": "存在红色项，请优先处理路由未挂载或服务不可达。"}
    elif "warn" in levels:
        overall = {"level": "warn", "label": "需关注", "hint": "存在黄色项，功能可能不完整，建议尽快补齐配置或挂载。"}
    else:
        overall = {
            "level": "ok" if node_status == "connected" else "info",
            "label": "主路径可用" if matrix_count > 0 else "仅主栈",
            "hint": (
                "FastAPI 主路径健康；seo-backend 已连通。"
                if node_status == "connected"
                else "FastAPI 主路径可用；seo-backend 为可选旁路，未启用不影响主功能。"
            ),
        }

    return {
        "primary": primary,
        "overall": overall,
        "fastapi_routes": {
            "seo_matrix": matrix_count,
            "seo_advanced": advanced_count,
            "total_api": total_api,
        },
        "checks": {
            "primary": primary_h,
            "seo_matrix_routes": matrix_h,
            "seo_advanced_routes": advanced_h,
            "seo_backend": node_h,
        },
        "seo_backend": {
            "url": seo_backend_url,
            "status": node_status,
            "detail": node_detail,
            "proxy_path": f"{settings.API_V1_PREFIX}/super-admin/seo-proxy/",
        },
        "acquisition_panel": _build_acquisition_api_panel(),
        "guidance": [
            "判定图例：绿=正常 · 黄=偏少/降级 · 红=异常/不可达 · 灰=可选未启用",
            "新功能优先实现于 FastAPI（/api/v1/seo-matrix 与 /api/v1/seo/*）",
            "seo-backend 仅作历史矩阵 Node 服务，通过 super-admin/seo-proxy 代理",
            "本机 Node seo-backend 常见端口为 3001；官网 Vite 常用 3000，勿混用",
            "生产环境请配置 SEO_BACKEND_URL 并监控 node_status",
        ],
    }
