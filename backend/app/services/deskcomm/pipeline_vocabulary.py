# -*- coding: utf-8 -*-
"""租户 Pipeline 词汇（Deskcomm multi-nicho → 建材外贸默认 + 覆盖）。"""
from __future__ import annotations

import json
from typing import Any

DEFAULT_VOCABULARY: dict[str, Any] = {
    "industry": "building_materials_export",
    "lead_label": "询盘",
    "qualified_label": "已联系",
    "proposal_label": "已报价",
    "sample_label": "样品",
    "negotiation_label": "谈判",
    "won_label": "成交",
    "lost_label": "流失",
    "stages": [
        {"key": "inquiry", "label": "询盘"},
        {"key": "contacted", "label": "已联系"},
        {"key": "quoted", "label": "已报价"},
        {"key": "sample", "label": "样品"},
        {"key": "negotiation", "label": "谈判"},
        {"key": "won", "label": "成交"},
        {"key": "lost", "label": "流失"},
    ],
}


def _load_tenant_settings(db, tenant_id: str) -> dict[str, Any]:
    if db is None or not hasattr(db, "query"):
        return {}
    try:
        from app.models.tenant import Tenant

        row = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
        if not row or not row.settings:
            return {}
        try:
            data = json.loads(row.settings) if isinstance(row.settings, str) else dict(row.settings)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    except Exception:
        return {}


def get_vocabulary(db, tenant_id: str) -> dict[str, Any]:
    settings = _load_tenant_settings(db, tenant_id)
    custom = settings.get("pipeline_vocabulary") or {}
    merged = dict(DEFAULT_VOCABULARY)
    if isinstance(custom, dict) and custom:
        merged.update(custom)
        merged["source"] = "tenant_override"
    else:
        merged["source"] = "default_building_materials"
    merged["tenant_id"] = str(tenant_id or "")
    return merged


def set_vocabulary(db, tenant_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(patch, dict) or not patch:
        raise ValueError("empty_vocabulary_patch")
    allowed = set(DEFAULT_VOCABULARY.keys()) | {"stages"}
    clean = {k: v for k, v in patch.items() if k in allowed}
    if not clean:
        raise ValueError("no_allowed_keys")
    from app.models.tenant import Tenant

    row = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
    if not row:
        raise ValueError("tenant_not_found")
    settings: dict[str, Any] = {}
    if row.settings:
        try:
            settings = json.loads(row.settings) if isinstance(row.settings, str) else dict(row.settings)
        except Exception:
            settings = {}
    if not isinstance(settings, dict):
        settings = {}
    current = settings.get("pipeline_vocabulary") or {}
    if not isinstance(current, dict):
        current = {}
    current.update(clean)
    settings["pipeline_vocabulary"] = current
    row.settings = json.dumps(settings, ensure_ascii=False)
    db.commit()
    return get_vocabulary(db, tenant_id)
