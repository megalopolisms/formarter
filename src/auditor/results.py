"""
Audit Result Storage and Management.

Handles:
- Individual audit results per document
- Real-time audit log for Claude Code integration
- Save/load to JSON files
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from .checklist import CheckStatus, CheckCategory


@dataclass
class ItemResult:
    """Result of checking a single checklist item."""
    item_id: int
    category: str  # Category name as string
    description: str
    rule_citation: str
    status: str  # CheckStatus value as string
    message: str = ""
    line_number: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "item_id": self.item_id,
            "category": self.category,
            "description": self.description,
            "rule_citation": self.rule_citation,
            "status": self.status,
            "message": self.message,
            "line_number": self.line_number
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ItemResult":
        """Create from dictionary."""
        return cls(
            item_id=data["item_id"],
            category=data["category"],
            description=data["description"],
            rule_citation=data["rule_citation"],
            status=data["status"],
            message=data.get("message", ""),
            line_number=data.get("line_number")
        )


@dataclass
class AuditResult:
    """Complete audit result for a document."""
    document_id: str
    document_name: str
    audit_date: str
    checklist_version: str = "1.0"
    total_items: int = 107
    passed: int = 0
    failed: int = 0
    warnings: int = 0
    manual_review: int = 0
    not_applicable: int = 0
    items: List[ItemResult] = field(default_factory=list)
    critical_issues: List[str] = field(default_factory=list)

    @property
    def score(self) -> float:
        """Calculate compliance score as percentage."""
        checkable = self.passed + self.failed + self.warnings
        if checkable == 0:
            return 0.0
        return round((self.passed / checkable) * 100, 1)

    @property
    def checked_count(self) -> int:
        """Number of items that were checked (not manual/n/a)."""
        return self.passed + self.failed + self.warnings

    def add_result(self, result: ItemResult):
        """Add an item result and update counts."""
        self.items.append(result)
        if result.status == CheckStatus.PASS.value:
            self.passed += 1
        elif result.status == CheckStatus.FAIL.value:
            self.failed += 1
        elif result.status == CheckStatus.WARNING.value:
            self.warnings += 1
        elif result.status == CheckStatus.MANUAL.value:
            self.manual_review += 1
        elif result.status == CheckStatus.NOT_APPLICABLE.value:
            self.not_applicable += 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "document_id": self.document_id,
            "document_name": self.document_name,
            "audit_date": self.audit_date,
            "checklist_version": self.checklist_version,
            "total_items": self.total_items,
            "summary": {
                "passed": self.passed,
                "failed": self.failed,
                "warnings": self.warnings,
                "manual_review": self.manual_review,
                "not_applicable": self.not_applicable,
                "score": self.score,
                "checked_count": self.checked_count
            },
            "critical_issues": self.critical_issues,
            "items": [item.to_dict() for item in self.items]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditResult":
        """Create from dictionary."""
        result = cls(
            document_id=data["document_id"],
            document_name=data["document_name"],
            audit_date=data["audit_date"],
            checklist_version=data.get("checklist_version", "1.0"),
            total_items=data.get("total_items", 107)
        )
        summary = data.get("summary", {})
        result.passed = summary.get("passed", 0)
        result.failed = summary.get("failed", 0)
        result.warnings = summary.get("warnings", 0)
        result.manual_review = summary.get("manual_review", 0)
        result.not_applicable = summary.get("not_applicable", 0)
        result.critical_issues = data.get("critical_issues", [])
        result.items = [ItemResult.from_dict(item) for item in data.get("items", [])]
        return result


@dataclass
class AuditLog:
    """
    Real-time audit log for Claude Code integration.

    This is updated as the audit progresses, allowing the main agent
    to check status mid-verification.
    """
    session_id: str
    started: str
    document_id: str
    document_name: str
    status: str = "in_progress"  # in_progress, completed, failed
    progress: Dict[str, Any] = field(default_factory=lambda: {
        "total_items": 107,
        "items_checked": 0,
        "percent_complete": 0
    })
    summary: Dict[str, Any] = field(default_factory=lambda: {
        "passed": 0,
        "failed": 0,
        "warnings": 0,
        "manual_review": 0,
        "score": 0.0
    })
    results: List[Dict[str, Any]] = field(default_factory=list)
    critical_issues: List[str] = field(default_factory=list)
    last_updated: str = ""

    def update_progress(self, items_checked: int):
        """Update progress information."""
        self.progress["items_checked"] = items_checked
        self.progress["percent_complete"] = round(
            (items_checked / self.progress["total_items"]) * 100
        )
        self.last_updated = datetime.now().isoformat()

    def add_item_result(self, result: ItemResult):
        """Add a result and update summary."""
        self.results.append(result.to_dict())

        if result.status == CheckStatus.PASS.value:
            self.summary["passed"] += 1
        elif result.status == CheckStatus.FAIL.value:
            self.summary["failed"] += 1
            # Add to critical issues if it's a key item
            if result.item_id in [12, 15, 21, 54, 65]:  # Critical item IDs
                self.critical_issues.append(f"#{result.item_id}: {result.message}")
        elif result.status == CheckStatus.WARNING.value:
            self.summary["warnings"] += 1
        elif result.status == CheckStatus.MANUAL.value:
            self.summary["manual_review"] += 1

        # Update score
        checkable = self.summary["passed"] + self.summary["failed"] + self.summary["warnings"]
        if checkable > 0:
            self.summary["score"] = round((self.summary["passed"] / checkable) * 100, 1)

        self.update_progress(len(self.results))

    def complete(self):
        """Mark audit as complete."""
        self.status = "completed"
        self.last_updated = datetime.now().isoformat()

    def fail(self, error: str):
        """Mark audit as failed."""
        self.status = "failed"
        self.critical_issues.append(f"Audit failed: {error}")
        self.last_updated = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "session_id": self.session_id,
            "started": self.started,
            "document_id": self.document_id,
            "document_name": self.document_name,
            "status": self.status,
            "progress": self.progress,
            "summary": self.summary,
            "results": self.results,
            "critical_issues": self.critical_issues,
            "last_updated": self.last_updated
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditLog":
        """Create from dictionary."""
        log = cls(
            session_id=data["session_id"],
            started=data["started"],
            document_id=data["document_id"],
            document_name=data["document_name"],
            status=data.get("status", "in_progress")
        )
        log.progress = data.get("progress", log.progress)
        log.summary = data.get("summary", log.summary)
        log.results = data.get("results", [])
        log.critical_issues = data.get("critical_issues", [])
        log.last_updated = data.get("last_updated", "")
        return log

    @classmethod
    def create_new(cls, document_id: str, document_name: str) -> "AuditLog":
        """Create a new audit log session."""
        now = datetime.now()
        return cls(
            session_id=f"audit-{now.strftime('%Y-%m-%d-%H%M%S')}",
            started=now.isoformat(),
            document_id=document_id,
            document_name=document_name,
            last_updated=now.isoformat()
        )


# =============================================================================
# STORAGE FUNCTIONS
# =============================================================================

def get_audits_dir(storage_dir: Path) -> Path:
    """Get the audits directory, creating if needed."""
    audits_dir = storage_dir / "audits"
    audits_dir.mkdir(parents=True, exist_ok=True)
    return audits_dir


def save_audit_result(result: AuditResult, storage_dir: Path) -> Path:
    """
    Save audit result to JSON file.

    Args:
        result: The audit result to save
        storage_dir: Base storage directory (e.g., ~/Dropbox/Formarter Folder/)

    Returns:
        Path to the saved file
    """
    audits_dir = get_audits_dir(storage_dir)

    # Use document_id for filename, sanitized
    safe_id = result.document_id.replace("/", "_").replace("\\", "_")
    audit_file = audits_dir / f"{safe_id}.json"

    with open(audit_file, "w", encoding="utf-8") as f:
        json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)

    return audit_file


def load_audit_result(document_id: str, storage_dir: Path) -> Optional[AuditResult]:
    """
    Load audit result from JSON file.

    Args:
        document_id: The document ID
        storage_dir: Base storage directory

    Returns:
        AuditResult or None if not found
    """
    audits_dir = get_audits_dir(storage_dir)

    safe_id = document_id.replace("/", "_").replace("\\", "_")
    audit_file = audits_dir / f"{safe_id}.json"

    if not audit_file.exists():
        return None

    try:
        with open(audit_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return AuditResult.from_dict(data)
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error loading audit result: {e}")
        return None


def save_audit_log(log: AuditLog, storage_dir: Path) -> Path:
    """
    Save/update the real-time audit log.

    This overwrites the existing log file, allowing real-time monitoring.

    Args:
        log: The audit log to save
        storage_dir: Base storage directory

    Returns:
        Path to the saved file
    """
    audits_dir = get_audits_dir(storage_dir)
    log_file = audits_dir / "audit_log.json"

    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(log.to_dict(), f, indent=2, ensure_ascii=False)

    return log_file


def load_audit_log(storage_dir: Path) -> Optional[AuditLog]:
    """
    Load the current audit log.

    Args:
        storage_dir: Base storage directory

    Returns:
        AuditLog or None if not found
    """
    audits_dir = get_audits_dir(storage_dir)
    log_file = audits_dir / "audit_log.json"

    if not log_file.exists():
        return None

    try:
        with open(log_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return AuditLog.from_dict(data)
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error loading audit log: {e}")
        return None


def list_audit_results(storage_dir: Path) -> List[Dict[str, Any]]:
    """
    List all saved audit results with summary info.

    Returns list of dicts with document_id, document_name, audit_date, score.
    """
    audits_dir = get_audits_dir(storage_dir)
    results = []

    for audit_file in audits_dir.glob("*.json"):
        if audit_file.name == "audit_log.json":
            continue  # Skip the real-time log

        try:
            with open(audit_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            results.append({
                "document_id": data.get("document_id", ""),
                "document_name": data.get("document_name", ""),
                "audit_date": data.get("audit_date", ""),
                "score": data.get("summary", {}).get("score", 0.0)
            })
        except (json.JSONDecodeError, KeyError):
            continue

    return sorted(results, key=lambda x: x.get("audit_date", ""), reverse=True)
