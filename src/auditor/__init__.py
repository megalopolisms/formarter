"""
Auditor module for TRO Motion compliance checking.

This module provides:
- 107-item TRO Motion compliance checklist
- Automatic detection for ~30 checkable items
- Audit result storage and retrieval
- Real-time logging for Claude Code integration
"""

from .checklist import (
    CheckCategory,
    CheckStatus,
    ChecklistItem,
    TRO_CHECKLIST,
    get_checklist_by_category,
    get_auto_checkable_items,
)
from .results import (
    ItemResult,
    AuditResult,
    save_audit_result,
    load_audit_result,
    save_audit_log,
    load_audit_log,
)
from .detector import ComplianceDetector, AuditOptions

__all__ = [
    "CheckCategory",
    "CheckStatus",
    "ChecklistItem",
    "TRO_CHECKLIST",
    "get_checklist_by_category",
    "get_auto_checkable_items",
    "ItemResult",
    "AuditResult",
    "save_audit_result",
    "load_audit_result",
    "save_audit_log",
    "load_audit_log",
    "ComplianceDetector",
    "AuditOptions",
]
