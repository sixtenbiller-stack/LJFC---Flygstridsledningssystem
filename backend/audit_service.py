"""Audit service — records operator decisions with snapshot lineage."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from models import AuditRecord


class AuditService:
    def __init__(self) -> None:
        self._records: list[AuditRecord] = []
        self._counter = 0

    def approve(
        self,
        coa_id: str,
        source_state_id: str,
        operator_note: str = "",
        readiness_remaining_pct: float = 100.0,
        wave: int = 1,
    ) -> AuditRecord:
        self._counter += 1
        record = AuditRecord(
            decision_id=f"dec-{self._counter:03d}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            coa_id=coa_id,
            source_state_id=source_state_id,
            operator_note=operator_note,
            readiness_delta=f"Committed assets per {coa_id}",
            readiness_remaining_pct=readiness_remaining_pct,
            wave=wave,
        )
        self._records.append(record)
        return record

    def get_all(self) -> list[AuditRecord]:
        return list(self._records)

    def clear(self) -> None:
        self._records.clear()
        self._counter = 0
