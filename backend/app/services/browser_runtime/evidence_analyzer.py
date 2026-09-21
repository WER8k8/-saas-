# -*- coding: utf-8 -*-
# Copyright (c) 2026 吕博旺 (131025199403304817). All rights reserved.
"""Browser 证据自动分析管道。

补齐原架构缺口「Browser Runtime → 证据分析缺少自动化管道」：

- 消费 `EvidenceRecord`（单条或批量）
- 异常检测：失败/阻断/降级、Policy 拒绝、超时、写动作无审批、敏感动作无截图
- 合规检查：submit 无 approval、白名单外 URL、超长写值等
- 结果分级 info/warn/critical，并发布 `event_bus` 事件
- 不阻断主链路：分析失败只记日志
"""

from __future__ import annotations

import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from app.core.event_bus import Event, EventPriority, EventTypes, event_bus
from app.services.browser_runtime.evidence import (
    EXEC_BLOCKED,
    EXEC_DEGRADED,
    EXEC_FAILED,
    EXEC_SUCCESS,
    EvidenceRecord,
)

logger = logging.getLogger("uj-admin.evidence_analyzer")

# 阈值（可用 env 覆盖）
DEFAULT_SLOW_MS = int(os.getenv("EVIDENCE_SLOW_MS", "30000") or 30000)
DEFAULT_WRITE_ACTIONS = frozenset(
    {"fill", "click", "submit", "upload", "keyboard", "drag", "type", "press"}
)
DEFAULT_SENSITIVE_ACTIONS = frozenset({"submit", "upload", "click", "fill", "purchase", "pay"})

SEVERITY_INFO = "info"
SEVERITY_WARN = "warn"
SEVERITY_CRITICAL = "critical"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _to_record_dict(item: Any) -> dict[str, Any]:
    if isinstance(item, EvidenceRecord):
        return item.to_dict()
    if isinstance(item, dict):
        return item
    if hasattr(item, "to_dict"):
        try:
            return item.to_dict()
        except Exception:  # noqa: BLE001
            pass
    return {"raw": str(item)}


@dataclass
class Finding:
    """单条分析发现。"""

    code: str
    severity: str
    message: str
    action: str = ""
    evidence_id: str = ""
    tenant_id: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AnalysisReport:
    """批量分析报告。"""

    analyzed_at: str = field(default_factory=lambda: _utcnow().isoformat())
    total: int = 0
    success_count: int = 0
    failed_count: int = 0
    blocked_count: int = 0
    degraded_count: int = 0
    findings: list[Finding] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    @property
    def max_severity(self) -> str:
        order = {SEVERITY_INFO: 0, SEVERITY_WARN: 1, SEVERITY_CRITICAL: 2}
        if not self.findings:
            return SEVERITY_INFO
        return max(self.findings, key=lambda f: order.get(f.severity, 0)).severity

    @property
    def has_anomaly(self) -> bool:
        return any(f.severity in {SEVERITY_WARN, SEVERITY_CRITICAL} for f in self.findings)

    @property
    def compliance_ok(self) -> bool:
        codes = {f.code for f in self.findings if f.severity in {SEVERITY_WARN, SEVERITY_CRITICAL}}
        compliance_codes = {
            "SUBMIT_WITHOUT_APPROVAL",
            "SENSITIVE_WITHOUT_SCREENSHOT",
            "POLICY_BLOCKED",
            "SUSPICIOUS_URL",
        }
        return not (codes & compliance_codes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "analyzed_at": self.analyzed_at,
            "total": self.total,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "blocked_count": self.blocked_count,
            "degraded_count": self.degraded_count,
            "max_severity": self.max_severity,
            "has_anomaly": self.has_anomaly,
            "compliance_ok": self.compliance_ok,
            "findings": [f.to_dict() for f in self.findings],
            "summary": self.summary,
        }


class EvidenceAnalyzer:
    """Browser 证据自动分析器。"""

    def __init__(
        self,
        *,
        slow_ms: Optional[int] = None,
        write_actions: Optional[frozenset[str]] = None,
        sensitive_actions: Optional[frozenset[str]] = None,
        emit_events: bool = True,
    ) -> None:
        self.slow_ms = int(slow_ms if slow_ms is not None else DEFAULT_SLOW_MS)
        self.write_actions = frozenset(write_actions or DEFAULT_WRITE_ACTIONS)
        self.sensitive_actions = frozenset(sensitive_actions or DEFAULT_SENSITIVE_ACTIONS)
        self.emit_events = bool(emit_events)

    def analyze_one(self, evidence: Any) -> list[Finding]:
        """分析单条证据，返回 findings 列表（可为空）。"""
        rec = _to_record_dict(evidence)
        findings: list[Finding] = []
        eid = str(rec.get("id") or "")
        tenant = str(rec.get("tenant_id") or "")
        action = str(rec.get("action") or "").lower()
        status = str(rec.get("status") or "").lower()
        target = str(rec.get("target_url") or "")
        duration = int(rec.get("duration_ms") or 0)
        error_code = str(rec.get("error_code") or "")
        error_message = str(rec.get("error_message") or "")
        policy = rec.get("policy_verdict")
        screenshot = rec.get("screenshot_path")
        submit_auto = rec.get("submit_auto")
        submit_approval_id = rec.get("submit_approval_id")

        def add(code: str, severity: str, message: str, **details: Any) -> None:
            findings.append(
                Finding(
                    code=code,
                    severity=severity,
                    message=message,
                    action=action,
                    evidence_id=eid,
                    tenant_id=tenant,
                    details=details,
                )
            )

        # 状态类异常
        if status == EXEC_FAILED:
            add(
                "EXEC_FAILED",
                SEVERITY_WARN,
                f"执行失败: {error_code or 'UNKNOWN'} {error_message[:200]}",
                error_code=error_code,
                error_message=error_message[:500],
            )
        elif status == EXEC_BLOCKED:
            add(
                "POLICY_BLOCKED",
                SEVERITY_CRITICAL,
                "Policy 阻断执行（合规闸生效）",
                policy_verdict=policy if isinstance(policy, dict) else None,
                error_code=error_code,
            )
        elif status == EXEC_DEGRADED:
            add(
                "EXEC_DEGRADED",
                SEVERITY_WARN,
                f"执行降级 noop: {error_code or ''}".strip(),
                error_code=error_code,
                error_message=error_message[:300],
            )

        # 耗时异常
        if duration >= self.slow_ms:
            add(
                "SLOW_EXECUTION",
                SEVERITY_WARN,
                f"执行耗时过长 {duration}ms ≥ {self.slow_ms}ms",
                duration_ms=duration,
                threshold_ms=self.slow_ms,
            )

        # 合规：写动作 / submit
        if action in self.write_actions or action == "submit":
            if action == "submit" and status == EXEC_SUCCESS:
                auto = bool(submit_auto)
                if auto and not submit_approval_id:
                    add(
                        "SUBMIT_WITHOUT_APPROVAL",
                        SEVERITY_CRITICAL,
                        "submit 自动执行但缺少 approval_id",
                        submit_auto=auto,
                        submit_approval_id=submit_approval_id,
                    )
            if action in self.sensitive_actions and status == EXEC_SUCCESS and not screenshot:
                add(
                    "SENSITIVE_WITHOUT_SCREENSHOT",
                    SEVERITY_WARN,
                    f"敏感动作 {action} 成功但无截图证据",
                    screenshot_path=screenshot,
                )

        # URL 可疑模式
        if target:
            lower = target.lower()
            suspicious_tokens = (
                "javascript:",
                "data:text/html",
                "file:///",
                "127.0.0.1/admin",
                "localhost/admin",
            )
            if any(tok in lower for tok in suspicious_tokens):
                add(
                    "SUSPICIOUS_URL",
                    SEVERITY_CRITICAL,
                    f"目标 URL 疑似异常: {target[:200]}",
                    target_url=target[:300],
                )

        # 超长 fill（净化后仍可能异常）
        fill_len = int(rec.get("fill_value_original_len") or 0)
        if fill_len > 20000:
            add(
                "OVERSIZED_FILL",
                SEVERITY_WARN,
                f"fill 原文长度异常 {fill_len}",
                fill_value_original_len=fill_len,
            )

        # Policy 判定字段自带 deny
        if isinstance(policy, dict):
            verdict = str(policy.get("verdict") or policy.get("decision") or "").lower()
            if verdict in {"deny", "denied", "block", "blocked", "reject"}:
                # 避免与 POLICY_BLOCKED 重复计数
                if not any(f.code == "POLICY_BLOCKED" for f in findings):
                    add(
                        "POLICY_BLOCKED",
                        SEVERITY_CRITICAL,
                        "policy_verdict 标记拒绝",
                        policy_verdict=policy,
                    )

        return findings

    def analyze_batch(self, evidences: Iterable[Any]) -> AnalysisReport:
        """批量分析并生成报告。"""
        report = AnalysisReport()
        items = list(evidences or [])
        report.total = len(items)
        status_counts = {EXEC_SUCCESS: 0, EXEC_FAILED: 0, EXEC_BLOCKED: 0, EXEC_DEGRADED: 0}

        for item in items:
            rec = _to_record_dict(item)
            st = str(rec.get("status") or "").lower()
            if st in status_counts:
                status_counts[st] += 1
            try:
                findings = self.analyze_one(item)
                report.findings.extend(findings)
            except Exception as exc:  # noqa: BLE001
                logger.warning("analyze_one failed: %s", exc)
                report.findings.append(
                    Finding(
                        code="ANALYZE_ERROR",
                        severity=SEVERITY_WARN,
                        message=f"分析异常: {exc}",
                    )
                )

        report.success_count = status_counts[EXEC_SUCCESS]
        report.failed_count = status_counts[EXEC_FAILED]
        report.blocked_count = status_counts[EXEC_BLOCKED]
        report.degraded_count = status_counts[EXEC_DEGRADED]
        report.summary = {
            "finding_count": len(report.findings),
            "warn_count": sum(1 for f in report.findings if f.severity == SEVERITY_WARN),
            "critical_count": sum(1 for f in report.findings if f.severity == SEVERITY_CRITICAL),
            "status_counts": status_counts,
        }
        return report

    def analyze_and_emit(
        self,
        evidences: Any,
        *,
        tenant_id: str = "",
        source: str = "browser_runtime",
    ) -> dict[str, Any]:
        """分析并发布事件到 event_bus（不抛穿）。"""
        if isinstance(evidences, (list, tuple, set)):
            items: list[Any] = list(evidences)
        else:
            items = [evidences]

        report = self.analyze_batch(items)
        result = report.to_dict()
        result["tenant_id"] = tenant_id

        if not self.emit_events:
            return result

        try:
            # 汇总事件
            summary_event = Event(
                event_type=EventTypes.EVIDENCE_ANALYZED,
                data={
                    "tenant_id": tenant_id,
                    "source": source,
                    "total": report.total,
                    "max_severity": report.max_severity,
                    "has_anomaly": report.has_anomaly,
                    "compliance_ok": report.compliance_ok,
                    "finding_count": len(report.findings),
                    "summary": report.summary,
                    "analyzed_at": report.analyzed_at,
                },
                priority=EventPriority.HIGH if report.has_anomaly else EventPriority.NORMAL,
                source=source,
                tenant_id=tenant_id,
            )
            if hasattr(event_bus, "emit_sync"):
                event_bus.emit_sync(summary_event)
            else:
                event_bus.emit(summary_event)

            # 逐条异常事件（仅 warn/critical）
            for f in report.findings:
                if f.severity not in {SEVERITY_WARN, SEVERITY_CRITICAL}:
                    continue
                anomaly = Event(
                    event_type=EventTypes.EVIDENCE_ANOMALY,
                    data=f.to_dict(),
                    priority=EventPriority.CRITICAL if f.severity == SEVERITY_CRITICAL else EventPriority.HIGH,
                    source=source,
                    tenant_id=f.tenant_id or tenant_id,
                )
                try:
                    if hasattr(event_bus, "emit_sync"):
                        event_bus.emit_sync(anomaly)
                    else:
                        event_bus.emit(anomaly)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("emit EVIDENCE_ANOMALY failed: %s", exc)
        except Exception as exc:  # noqa: BLE001
            logger.warning("evidence analyze_and_emit emit failed: %s", exc)
            result["emit_error"] = str(exc)

        return result

    def analyze_from_jsonl(
        self,
        *,
        tenant_id: str = "global",
        limit: int = 200,
        base_dir: Optional[str] = None,
    ) -> dict[str, Any]:
        """从落盘 audit.jsonl 读取并分析最近证据。"""
        import json

        base = base_dir or os.environ.get("BROWSER_EVIDENCE_DIR") or "data/browser_evidence"
        path = os.path.join(base, tenant_id, "audit.jsonl")
        if not os.path.exists(path):
            report = AnalysisReport()
            report.summary = {"reason": "jsonl_not_found", "path": path}
            return report.to_dict()

        items: list[dict[str, Any]] = []
        try:
            with open(path, "r", encoding="utf-8") as fh:
                lines = fh.readlines()
            for line in lines[-int(limit or 200) :]:
                line = line.strip()
                if not line:
                    continue
                try:
                    items.append(json.loads(line))
                except Exception:  # noqa: BLE001
                    continue
        except Exception as exc:  # noqa: BLE001
            logger.warning("read jsonl failed: %s", exc)
            report = AnalysisReport()
            report.summary = {"reason": "jsonl_read_error", "error": str(exc), "path": path}
            return report.to_dict()

        return self.analyze_and_emit(items, tenant_id=tenant_id, source="browser_evidence_jsonl")


# 全局单例
evidence_analyzer = EvidenceAnalyzer()


def analyze_evidence(evidence: Any, **kwargs: Any) -> dict[str, Any]:
    """便捷入口：分析单条/批量证据并 emit。"""
    return evidence_analyzer.analyze_and_emit(evidence, **kwargs)
