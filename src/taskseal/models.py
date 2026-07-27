from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


SCHEMA_VERSION = "0.1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class WorkItemValidationError(ValueError):
    pass


class WorkStatus(str, Enum):
    DRAFT = "draft"
    PLANNING = "planning"
    AWAITING_AUTHORIZATION = "awaiting_authorization"
    AUTHORIZED = "authorized"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    REPAIRING = "repairing"
    BLOCKED = "blocked"
    ACCEPTED = "accepted"
    CANCELLED = "cancelled"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Resource:
    id: str
    kind: str
    locator: str
    allowed_actions: List[str]
    revision: Optional[str] = None


@dataclass
class AuthorizationRequest:
    subject: str
    resource_ids: List[str]
    actions: List[str]
    conditions: List[str] = field(default_factory=list)
    expires_at: Optional[str] = None
    parent_authorization_id: Optional[str] = None


@dataclass
class Authorization:
    id: str
    subject: str
    resource_ids: List[str]
    actions: List[str]
    conditions: List[str]
    expires_at: Optional[str]
    granted_by: str
    status: str = "granted"
    parent_authorization_id: Optional[str] = None
    granted_at: str = field(default_factory=utc_now)


@dataclass
class Artifact:
    id: str
    kind: str
    uri: str
    revision: str
    produced_by: str


@dataclass
class Evidence:
    id: str
    kind: str
    uri: str
    supports: List[str]
    resource_revision: str
    collected_by: str
    observed_at: str = field(default_factory=utc_now)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AcceptanceCriterion:
    id: str
    statement: str
    required_evidence_kinds: List[str] = field(default_factory=list)
    evidence_ids: List[str] = field(default_factory=list)
    status: str = "pending"
    verified_by: Optional[str] = None


@dataclass
class PlanStep:
    id: str
    summary: str
    status: str = "pending"
    executor: Optional[str] = None


@dataclass
class WorkItem:
    id: str
    goal: str
    requested_by: str
    resources: List[Resource]
    acceptance: List[AcceptanceCriterion]
    schema_version: str = SCHEMA_VERSION
    risk: RiskLevel = RiskLevel.LOW
    risk_reasons: List[str] = field(default_factory=list)
    prohibited_actions: List[str] = field(default_factory=list)
    status: WorkStatus = WorkStatus.DRAFT
    plan: List[PlanStep] = field(default_factory=list)
    authorizations: List[Authorization] = field(default_factory=list)
    artifacts: List[Artifact] = field(default_factory=list)
    evidence: List[Evidence] = field(default_factory=list)
    executor_ids: List[str] = field(default_factory=list)
    next_action: Optional[str] = None
    revision: int = 0
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    @classmethod
    def create(
        cls,
        goal: str,
        requested_by: str,
        resources: List[Resource],
        acceptance: List[AcceptanceCriterion],
        *,
        risk: RiskLevel = RiskLevel.LOW,
        risk_reasons: Optional[List[str]] = None,
        prohibited_actions: Optional[List[str]] = None,
        work_item_id: Optional[str] = None,
    ) -> "WorkItem":
        return cls(
            id=work_item_id or f"work-{uuid4().hex[:12]}",
            goal=goal,
            requested_by=requested_by,
            resources=resources,
            acceptance=acceptance,
            risk=risk,
            risk_reasons=risk_reasons or [],
            prohibited_actions=prohibited_actions or [],
        )

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["risk"] = self.risk.value
        return data

    def validate(self, *, require_initial: bool = False) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise WorkItemValidationError(
                f"unsupported schema version: {self.schema_version}"
            )
        if not isinstance(self.status, WorkStatus):
            raise WorkItemValidationError("status is invalid")
        if not isinstance(self.risk, RiskLevel):
            raise WorkItemValidationError("risk is invalid")
        if not isinstance(self.goal, str) or not self.goal.strip():
            raise WorkItemValidationError("goal must not be empty")
        if (
            not isinstance(self.requested_by, str)
            or not self.requested_by.strip()
        ):
            raise WorkItemValidationError("requested_by must not be empty")
        if not self.acceptance:
            raise WorkItemValidationError(
                "at least one acceptance criterion is required"
            )
        if require_initial:
            if self.status != WorkStatus.DRAFT:
                raise WorkItemValidationError(
                    "new work items must start in draft"
                )
            if self.revision != 0:
                raise WorkItemValidationError(
                    "new work items must start at revision zero"
                )
            if self.plan or self.authorizations or self.artifacts or self.evidence:
                raise WorkItemValidationError(
                    "new work items cannot contain execution state"
                )

        self._require_unique("resource", [item.id for item in self.resources])
        self._require_unique("plan step", [item.id for item in self.plan])
        self._require_unique(
            "authorization", [item.id for item in self.authorizations]
        )
        self._require_unique("artifact", [item.id for item in self.artifacts])
        self._require_unique("evidence", [item.id for item in self.evidence])
        self._require_unique(
            "acceptance criterion", [item.id for item in self.acceptance]
        )

        resource_ids = {item.id for item in self.resources}
        resources_by_id = {item.id: item for item in self.resources}
        authorization_ids = {item.id for item in self.authorizations}
        criterion_ids = {item.id for item in self.acceptance}
        evidence_ids = {item.id for item in self.evidence}

        for resource in self.resources:
            if not resource.id or not resource.kind or not resource.locator:
                raise WorkItemValidationError(
                    "resource id, kind and locator must not be empty"
                )
            if not resource.allowed_actions:
                raise WorkItemValidationError(
                    f"resource {resource.id} has no allowed actions"
                )

        for step in self.plan:
            if not step.summary:
                raise WorkItemValidationError(
                    f"plan step {step.id} has no summary"
                )
            if step.status not in {
                "pending",
                "running",
                "completed",
                "failed",
                "skipped",
            }:
                raise WorkItemValidationError(
                    f"plan step {step.id} has invalid status {step.status}"
                )

        for authorization in self.authorizations:
            missing = set(authorization.resource_ids) - resource_ids
            if missing:
                raise WorkItemValidationError(
                    f"authorization {authorization.id} references unknown "
                    f"resources: {sorted(missing)}"
                )
            if not authorization.actions:
                raise WorkItemValidationError(
                    f"authorization {authorization.id} has no actions"
                )
            if not authorization.subject or not authorization.granted_by:
                raise WorkItemValidationError(
                    f"authorization {authorization.id} has incomplete identity"
                )
            if authorization.subject == authorization.granted_by:
                raise WorkItemValidationError(
                    f"authorization {authorization.id} is self-issued"
                )
            if authorization.conditions:
                raise WorkItemValidationError(
                    f"authorization {authorization.id} has unsupported conditions"
                )
            if authorization.status not in {"granted", "expired", "revoked"}:
                raise WorkItemValidationError(
                    f"authorization {authorization.id} has invalid status"
                )
            if (
                authorization.parent_authorization_id is not None
                and authorization.parent_authorization_id
                not in authorization_ids
            ):
                raise WorkItemValidationError(
                    f"authorization {authorization.id} references an "
                    "unknown parent"
                )
            for resource_id in authorization.resource_ids:
                extra_actions = set(authorization.actions) - set(
                    resources_by_id[resource_id].allowed_actions
                )
                if extra_actions:
                    raise WorkItemValidationError(
                        f"authorization {authorization.id} exceeds resource "
                        f"{resource_id}: {sorted(extra_actions)}"
                    )
            prohibited = set(authorization.actions) & set(
                self.prohibited_actions
            )
            if prohibited:
                raise WorkItemValidationError(
                    f"authorization {authorization.id} contains prohibited "
                    f"actions: {sorted(prohibited)}"
                )

        for evidence in self.evidence:
            if (
                not evidence.kind
                or not evidence.uri
                or not evidence.collected_by
            ):
                raise WorkItemValidationError(
                    f"evidence {evidence.id} is incomplete"
                )
            if not evidence.supports:
                raise WorkItemValidationError(
                    f"evidence {evidence.id} supports no criteria"
                )
            missing = set(evidence.supports) - criterion_ids
            if missing:
                raise WorkItemValidationError(
                    f"evidence {evidence.id} supports unknown criteria: "
                    f"{sorted(missing)}"
                )
            if not evidence.resource_revision:
                raise WorkItemValidationError(
                    f"evidence {evidence.id} has no resource revision"
                )

        for artifact in self.artifacts:
            if (
                not artifact.kind
                or not artifact.uri
                or not artifact.revision
                or not artifact.produced_by
            ):
                raise WorkItemValidationError(
                    f"artifact {artifact.id} is incomplete"
                )

        for criterion in self.acceptance:
            if not criterion.statement:
                raise WorkItemValidationError(
                    f"criterion {criterion.id} has no statement"
                )
            if criterion.status not in {
                "pending",
                "passed",
                "failed",
                "blocked",
            }:
                raise WorkItemValidationError(
                    f"criterion {criterion.id} has invalid status"
                )
            missing = set(criterion.evidence_ids) - evidence_ids
            if missing:
                raise WorkItemValidationError(
                    f"criterion {criterion.id} references unknown evidence: "
                    f"{sorted(missing)}"
                )

        if self.status == WorkStatus.ACCEPTED:
            if any(item.status != "passed" for item in self.acceptance):
                raise WorkItemValidationError(
                    "accepted work items require every criterion to pass"
                )
            if any(not item.verified_by for item in self.acceptance):
                raise WorkItemValidationError(
                    "accepted work items require a verifier for every criterion"
                )
            incomplete = [
                item.id
                for item in self.plan
                if item.status not in {"completed", "skipped"}
            ]
            if incomplete:
                raise WorkItemValidationError(
                    f"accepted work item has incomplete plan steps: {incomplete}"
                )

    @staticmethod
    def _require_unique(kind: str, identifiers: List[str]) -> None:
        if any(not identifier for identifier in identifiers):
            raise WorkItemValidationError(f"{kind} id must not be empty")
        duplicates = sorted(
            identifier
            for identifier in set(identifiers)
            if identifiers.count(identifier) > 1
        )
        if duplicates:
            raise WorkItemValidationError(
                f"duplicate {kind} ids: {duplicates}"
            )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkItem":
        value = dict(data)
        value.setdefault("schema_version", SCHEMA_VERSION)
        value["status"] = WorkStatus(value["status"])
        value["risk"] = RiskLevel(value["risk"])
        value["resources"] = [Resource(**item) for item in value["resources"]]
        value["acceptance"] = [
            AcceptanceCriterion(**item) for item in value["acceptance"]
        ]
        value["plan"] = [PlanStep(**item) for item in value.get("plan", [])]
        authorizations = []
        for item in value.get("authorizations", []):
            authorization = dict(item)
            if "granted_by" not in authorization:
                authorization["granted_by"] = "legacy-unverified"
                authorization["conditions"] = []
                if authorization.get("status") == "granted":
                    authorization["status"] = "revoked"
            authorizations.append(Authorization(**authorization))
        value["authorizations"] = authorizations
        value["artifacts"] = [
            Artifact(**item) for item in value.get("artifacts", [])
        ]
        value["evidence"] = [
            Evidence(**item) for item in value.get("evidence", [])
        ]
        work_item = cls(**value)
        work_item.validate()
        return work_item
