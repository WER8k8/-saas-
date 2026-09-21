# -*- coding: utf-8 -*-
"""Handoff 闸门 G1–G4（中英关键词 + 纯函数；G2 无模型时诚实 degraded）。"""
from __future__ import annotations

import re
from typing import Any

# G1：用户明确要人工
G1_PATTERN = re.compile(
    r"(转人工|人工客服|找人工|要人工|真人|客服在吗|别机器人|不要机器人|"
    r"human|agent|real\s*person|live\s*agent|talk\s*to\s*someone|speak\s*to\s*a\s*human)",
    re.I,
)

# G4 法务/合规词
G4_LEGAL_PATTERN = re.compile(
    r"(律师|起诉|法院|合同纠纷|索赔|投诉到|315|律师函|"
    r"lawsuit|attorney|lawyer|legal\s*action|sue\s*you|consumer\s*protection)",
    re.I,
)

# G3 不确定话术
UNCERTAINTY_PATTERN = re.compile(
    r"(我不确定|无法确认|建议您咨询|可能不准确|仅供参考|"
    r"i'?m not sure|not certain|cannot confirm|as an ai)",
    re.I,
)

DEFAULT_CONFIDENCE_THRESHOLD = 0.45


def _check_g1(text: str) -> bool:
    return bool(text and G1_PATTERN.search(text))


def _check_g4_legal(text: str) -> bool:
    return bool(text and G4_LEGAL_PATTERN.search(text))


def _check_g3(output_text: str, confidence: float, threshold: float) -> bool:
    low = isinstance(confidence, (int, float)) and float(confidence) < float(threshold)
    return bool(low or (output_text and UNCERTAINTY_PATTERN.search(output_text)))


def evaluate_handoff(
    *,
    inbound_text: str = "",
    output_text: str = "",
    confidence: float | None = None,
    sentiment_score: float | None = None,
    sentiment_threshold: float = -0.35,
    stage_requires_human: bool = False,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> dict[str, Any]:
    """返回 handoff 判定。情感无分数时 degraded=true，不假装测过。"""
    triggers: list[str] = []
    if _check_g1(inbound_text):
        triggers.append("g1_human_request")
    if _check_g4_legal(inbound_text):
        triggers.append("g4_legal")
    if stage_requires_human:
        triggers.append("g4_stage_requires_human")
    if _check_g3(output_text, confidence if confidence is not None else 1.0, confidence_threshold):
        triggers.append("g3_low_confidence")

    sentiment_degraded = sentiment_score is None
    if not sentiment_degraded and float(sentiment_score) < float(sentiment_threshold):
        triggers.append("g2_negative_sentiment")

    should_handoff = bool(triggers)
    return {
        "should_handoff": should_handoff,
        "triggers": triggers,
        "reason": ",".join(triggers) if triggers else "ai_continue",
        "degraded": {"sentiment": sentiment_degraded},
        "confidence_threshold": confidence_threshold,
        "sentiment_threshold": sentiment_threshold,
    }
