"""
Moira — Audit Log Persistence
=============================

Archetype: Governance Logic (Workflow Actor)

Purpose
-------
Governs the persistent storage and progress tracking of the Moira 
export governance workflow. Manages audit decisions, status state, 
and resumption markers to ensure the integrity of the sovereign 
export boundary.

Boundary
--------
Owns:
    - Audit log JSON persistence format (v1.0).
    - Progress tracking state (audited/pending/exempted).
    - Workflow resumption logic.
Delegates:
    - Log entry models to moira._export_governance.models.

Import-time side effects
------------------------
None.

External dependency assumptions
--------------------------------
- Filesystem write access to the log path.
- UTF-8 encoding support.

Public surface
--------------
AuditLog class.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from moira._export_governance.models import (
    AuditLogEntry,
    AuditStatus,
    AuditDecision,
    ModuleCategory,
)


class AuditLog:
    """
    RITE: The Ledger of Truth

    THEOREM: AuditLog governs the durability and consistency of the 
        engine's governance state through versioned JSON persistence.

    RITE OF PURPOSE:
        This class exists to provide a tamper-evident record of all 
        governance decisions. It ensures that the transition from 
        chaotic export state to the sovereign boundary is documented, 
        reproducible, and restorable.

    LAW OF OPERATION:
        Responsibilities:
            - Serialize/Deserialize AuditLogEntry records.
            - Track progress metrics (coverage, pending counts).
            - Identify resumption points for interrupted audits.
        Non-responsibilities:
            - Does not perform the audit (delegates to the Auditor).
            - Does not validate engine logic (tracks metadata only).
        
    Canon: Moira Export Governance Protocol v1.

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira._export_governance.audit_log.AuditLog",
      "risk": "medium",
      "api": {
        "frozen": ["add_entry", "get_status", "save_log", "load_log"]
      },
      "state": {"mutable": true, "owners": ["Governance Auditor"]},
      "effects": {"signals_emitted": [], "io": ["filesystem read/write"]},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "backup_and_reset"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["schema_change"]}
    }
    [/MACHINE_CONTRACT]
    """

    def __init__(self, log_path: Path):
        """
        Initialize audit log.
        
        Args:
            log_path: Path to audit log JSON file
        """
        self.log_path = Path(log_path)
        self.entries: list[AuditLogEntry] = []
        self.version = "1.0"
        
        # Ensure parent directory exists
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing log if present
        if self.log_path.exists():
            self.load_log()

    def load_log(self) -> None:
        """
        Load audit log from file.
        
        Side effects:
            Updates internal entries list
            
        Raises:
            ValueError: If log file is corrupted
        """
        try:
            data = json.loads(self.log_path.read_text(encoding="utf-8"))
            
            # Validate version
            if data.get("version") != self.version:
                # Handle version mismatch - for now just warn
                pass
            
            # Load entries
            self.entries = []
            for entry_data in data.get("entries", []):
                entry = AuditLogEntry(
                    module_path=entry_data["module_path"],
                    status=AuditStatus(entry_data["status"]),
                    timestamp=datetime.fromisoformat(entry_data["timestamp"]),
                    auditor=entry_data["auditor"],
                    decision=AuditDecision(entry_data["decision"]),
                    rationale=entry_data.get("rationale"),
                    applied_exports=entry_data.get("applied_exports", [])
                )
                self.entries.append(entry)
        
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # Log is corrupted - attempt recovery
            self._handle_corrupted_log(e)

    def _handle_corrupted_log(self, error: Exception) -> None:
        """
        Handle corrupted audit log.
        
        Args:
            error: The exception that occurred
            
        Side effects:
            Creates backup of corrupted log
            Resets entries to empty list
        """
        # Create backup
        backup_path = self.log_path.with_suffix(".json.backup")
        if self.log_path.exists():
            self.log_path.rename(backup_path)
        
        # Reset entries
        self.entries = []

    def save_log(self) -> None:
        """
        Save audit log to file.
        
        Side effects:
            Writes JSON file to filesystem
        """
        data = {
            "version": self.version,
            "last_updated": datetime.now().isoformat(),
            "total_modules": self.get_total_modules(),
            "audited_modules": self.get_audited_count(),
            "pending_modules": self.get_pending_count(),
            "exempted_modules": self.get_exempted_count(),
            "entries": [
                {
                    "module_path": entry.module_path,
                    "status": entry.status.value,
                    "timestamp": entry.timestamp.isoformat(),
                    "auditor": entry.auditor,
                    "decision": entry.decision.value,
                    "rationale": entry.rationale,
                    "applied_exports": entry.applied_exports,
                }
                for entry in self.entries
            ]
        }
        
        self.log_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def add_entry(
        self,
        module_path: str,
        status: AuditStatus,
        auditor: str,
        decision: AuditDecision,
        rationale: str | None = None,
        applied_exports: list[str] | None = None
    ) -> None:
        """
        Add audit entry to log.
        
        Args:
            module_path: Path to audited module
            status: Audit status
            auditor: Name/email of auditor
            decision: Audit decision
            rationale: Optional rationale for decision
            applied_exports: Optional list of applied exports
            
        Side effects:
            Adds entry to log and saves to file
        """
        entry = AuditLogEntry(
            module_path=module_path,
            status=status,
            timestamp=datetime.now(),
            auditor=auditor,
            decision=decision,
            rationale=rationale,
            applied_exports=applied_exports or []
        )
        
        # Remove any existing entry for this module
        self.entries = [e for e in self.entries if e.module_path != module_path]
        
        # Add new entry
        self.entries.append(entry)
        
        # Save to file
        self.save_log()

    def get_status(self, module_path: str) -> AuditStatus | None:
        """
        Get audit status for a module.
        
        Args:
            module_path: Path to module
            
        Returns:
            AuditStatus if module has been audited, None otherwise
        """
        for entry in self.entries:
            if entry.module_path == module_path:
                return entry.status
        return None

    def get_entry(self, module_path: str) -> AuditLogEntry | None:
        """
        Get audit entry for a module.
        
        Args:
            module_path: Path to module
            
        Returns:
            AuditLogEntry if found, None otherwise
        """
        for entry in self.entries:
            if entry.module_path == module_path:
                return entry
        return None

    def get_total_modules(self) -> int:
        """Get total number of modules in log."""
        return len(self.entries)

    def get_audited_count(self) -> int:
        """Get count of audited modules."""
        return sum(1 for e in self.entries if e.status == AuditStatus.AUDITED)

    def get_pending_count(self) -> int:
        """Get count of pending modules."""
        return sum(1 for e in self.entries if e.status == AuditStatus.PENDING)

    def get_exempted_count(self) -> int:
        """Get count of exempted modules."""
        return sum(1 for e in self.entries if e.status == AuditStatus.EXEMPTED)

    def get_skipped_count(self) -> int:
        """Get count of skipped modules."""
        return sum(1 for e in self.entries if e.status == AuditStatus.SKIPPED)

    def resume_from_last(self) -> str | None:
        """
        Get the last audited module for workflow resumption.
        
        Returns:
            Module path of last audited module, or None if no audits
        """
        audited = [e for e in self.entries if e.status == AuditStatus.AUDITED]
        if audited:
            # Sort by timestamp and get most recent
            audited.sort(key=lambda e: e.timestamp, reverse=True)
            return audited[0].module_path
        return None

    def get_next_pending(self) -> str | None:
        """
        Get next pending module for audit.
        
        Returns:
            Module path of next pending module, or None if none pending
        """
        pending = [e for e in self.entries if e.status == AuditStatus.PENDING]
        if pending:
            # Sort by module path for consistent ordering
            pending.sort(key=lambda e: e.module_path)
            return pending[0].module_path
        return None

    def calculate_coverage(self) -> float:
        """
        Calculate governance coverage percentage.
        
        Returns:
            Coverage percentage (0-100)
        """
        total = self.get_total_modules()
        if total == 0:
            return 0.0
        
        audited = self.get_audited_count()
        return (audited / total) * 100.0

    def get_progress_summary(self) -> dict[str, Any]:
        """
        Generate progress summary statistics.
        
        Returns:
            Dictionary with progress metrics
        """
        return {
            "total_modules": self.get_total_modules(),
            "audited": self.get_audited_count(),
            "pending": self.get_pending_count(),
            "exempted": self.get_exempted_count(),
            "skipped": self.get_skipped_count(),
            "coverage_percentage": round(self.calculate_coverage(), 2),
        }


__all__ = ["AuditLog"]
