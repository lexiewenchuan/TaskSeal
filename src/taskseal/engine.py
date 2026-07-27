from __future__ import annotations

from typing import Iterable

from .acceptance import AcceptanceError, Acceptor
from .models import (
    Artifact,
    Authorization,
    AuthorizationRequest,
    Evidence,
    PlanStep,
    WorkItem,
    WorkStatus,
)
from .policy import PolicyEngine
from .state import transition
from .store import SQLiteWorkItemStore


class TaskSealEngine:
    def __init__(
        self,
        store: SQLiteWorkItemStore,
        *,
        policy: PolicyEngine,
        acceptor: Acceptor,
    ) -> None:
        self.store = store
        self.policy = policy
        self.acceptor = acceptor

    def create(self, work_item: WorkItem) -> WorkItem:
        self.store.create(work_item)
        return work_item

    def set_plan(self, work_item: WorkItem, steps: Iterable[PlanStep]) -> None:
        if work_item.status in {
            WorkStatus.DRAFT,
            WorkStatus.REPAIRING,
            WorkStatus.BLOCKED,
        }:
            transition(work_item, WorkStatus.PLANNING)
        if work_item.status != WorkStatus.PLANNING:
            raise ValueError("a plan can only be set while planning")
        work_item.plan = list(steps)
        self.store.save(
            work_item,
            event_kind="plan.updated",
            payload={"step_ids": [step.id for step in work_item.plan]},
        )

    def request_authorization(self, work_item: WorkItem) -> None:
        transition(work_item, WorkStatus.AWAITING_AUTHORIZATION)
        self.store.save(
            work_item, event_kind="authorization.requested"
        )

    def grant(
        self,
        work_item: WorkItem,
        request: AuthorizationRequest,
        *,
        granted_by: str,
    ) -> Authorization:
        if work_item.status not in {
            WorkStatus.AWAITING_AUTHORIZATION,
            WorkStatus.AUTHORIZED,
        }:
            raise ValueError("work item is not accepting authorizations")
        authorization = self.policy.grant(
            work_item, request, granted_by=granted_by
        )
        if work_item.status == WorkStatus.AWAITING_AUTHORIZATION:
            transition(work_item, WorkStatus.AUTHORIZED)
        self.store.save(
            work_item,
            event_kind="authorization.granted",
            payload={"authorization_id": authorization.id},
        )
        return authorization

    def start(self, work_item: WorkItem, *, executor: str) -> None:
        has_active_grant = self.policy.has_active_grant(
            work_item, subject=executor
        )
        if not has_active_grant:
            raise ValueError("executor has no active authorization")
        transition(work_item, WorkStatus.EXECUTING)
        if executor not in work_item.executor_ids:
            work_item.executor_ids.append(executor)
        self.store.save(
            work_item,
            event_kind="execution.started",
            payload={"executor": executor},
        )

    def revoke_authorization(
        self,
        work_item: WorkItem,
        *,
        authorization_id: str,
        revoked_by: str,
    ) -> None:
        authorization = self.policy.revoke(
            work_item,
            authorization_id=authorization_id,
            revoked_by=revoked_by,
        )
        self.store.save(
            work_item,
            event_kind="authorization.revoked",
            payload={
                "authorization_id": authorization.id,
                "revoked_by": revoked_by,
            },
        )

    def complete_step(
        self, work_item: WorkItem, *, step_id: str, executor: str
    ) -> None:
        if work_item.status != WorkStatus.EXECUTING:
            raise ValueError("plan steps can only complete while executing")
        step = next(
            (candidate for candidate in work_item.plan if candidate.id == step_id),
            None,
        )
        if step is None:
            raise KeyError(step_id)
        if step.executor is not None and step.executor != executor:
            raise ValueError("plan step belongs to another executor")
        if executor not in work_item.executor_ids:
            raise ValueError("executor is not active on this work item")
        if step.status not in {"pending", "running"}:
            raise ValueError(f"plan step cannot complete from {step.status}")
        step.status = "completed"
        self.store.save(
            work_item,
            event_kind="plan.step_completed",
            payload={"step_id": step_id, "executor": executor},
        )

    def attach_result(
        self,
        work_item: WorkItem,
        *,
        artifact: Artifact,
        evidence: Evidence,
    ) -> None:
        if work_item.status != WorkStatus.EXECUTING:
            raise ValueError("results can only be attached while executing")
        work_item.artifacts.append(artifact)
        work_item.evidence.append(evidence)
        for criterion in work_item.acceptance:
            if criterion.id in evidence.supports:
                criterion.evidence_ids.append(evidence.id)
        self.store.save(
            work_item,
            event_kind="evidence.attached",
            payload={
                "artifact_id": artifact.id,
                "evidence_id": evidence.id,
            },
        )

    def begin_verification(self, work_item: WorkItem) -> None:
        incomplete = [
            step.id
            for step in work_item.plan
            if step.status not in {"completed", "skipped"}
        ]
        if incomplete:
            raise ValueError(f"plan has incomplete steps: {incomplete}")
        if not work_item.artifacts or not work_item.evidence:
            raise ValueError("verification requires artifacts and evidence")
        transition(work_item, WorkStatus.VERIFYING)
        self.store.save(work_item, event_kind="verification.started")

    def accept(self, work_item: WorkItem, *, verifier: str) -> None:
        if work_item.status != WorkStatus.VERIFYING:
            raise ValueError("work item is not ready for verification")
        try:
            self.acceptor.verify(work_item, verifier=verifier)
        except AcceptanceError as error:
            transition(work_item, WorkStatus.REPAIRING)
            work_item.next_action = str(error)
            self.store.save(
                work_item,
                event_kind="verification.failed",
                payload={"reason": str(error)},
            )
            raise

        transition(work_item, WorkStatus.ACCEPTED)
        work_item.next_action = None
        self.store.save(
            work_item,
            event_kind="work_item.accepted",
            payload={"verifier": verifier},
        )
