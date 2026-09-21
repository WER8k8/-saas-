# -*- coding: utf-8 -*-
"""AI Sales Ops — Deskcomm 非重叠能力并入优丁（资格/Handoff/预算/守卫/飞轮）。"""
from .ai_budget import check_ai_budget
from .eligibility import AI_GATE_MODES, decide_eligibility, normalize_gate_mode
from .event_log import append_ai_sales_event
from .handoff_triggers import evaluate_handoff
from .knowledge_flywheel import record_resolved_conversation
from .pipeline_vocab import default_vocab, merge_vocab
from .whatsapp_guard import check_outbound_guard, detect_stop

__all__ = [
    "AI_GATE_MODES",
    "append_ai_sales_event",
    "check_ai_budget",
    "check_outbound_guard",
    "decide_eligibility",
    "default_vocab",
    "detect_stop",
    "evaluate_handoff",
    "merge_vocab",
    "normalize_gate_mode",
    "record_resolved_conversation",
]
