from __future__ import annotations

from typing import Dict

from .models import Evidence, WorkItem


class AcceptanceError(ValueError):
    pass


class Acceptor:
    """Accepts a task only when every criterion is supported by evidence."""

    def verify(self, work_item: WorkItem, *, verifier: str) -> None:
        if verifier in work_item.executor_ids:
            raise AcceptanceError("an executor cannot be the independent verifier")

        evidence_by_id: Dict[str, Evidence] = {
            item.id: item for item in work_item.evidence
        }
        failures = []

        for criterion in work_item.acceptance:
            attached = [
                evidence_by_id[evidence_id]
                for evidence_id in criterion.evidence_ids
                if evidence_id in evidence_by_id
            ]
            if not attached:
                criterion.status = "failed"
                failures.append(f"{criterion.id}: no evidence")
                continue

            unsupported = [
                evidence.id
                for evidence in attached
                if criterion.id not in evidence.supports
            ]
            if unsupported:
                criterion.status = "failed"
                failures.append(
                    f"{criterion.id}: evidence does not declare support "
                    f"{unsupported}"
                )
                continue

            kinds = {evidence.kind for evidence in attached}
            missing_kinds = sorted(
                set(criterion.required_evidence_kinds) - kinds
            )
            if missing_kinds:
                criterion.status = "failed"
                failures.append(
                    f"{criterion.id}: missing evidence kinds {missing_kinds}"
                )
                continue

            if any(not evidence.resource_revision for evidence in attached):
                criterion.status = "failed"
                failures.append(f"{criterion.id}: evidence has no revision")
                continue

            criterion.status = "passed"
            criterion.verified_by = verifier

        if failures:
            raise AcceptanceError("; ".join(failures))
