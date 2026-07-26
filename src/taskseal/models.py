from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkItem":
        value = dict(data)
        value["status"] = WorkStatus(value["status"])
        value["risk"] = RiskLevel(value["risk"])
        value["resources"] = [Resource(**item) for item in value["resources"]]
        value["acceptance"] = [
            AcceptanceCriterion(**item) for item in value["acceptance"]
        ]
        value["plan"] = [PlanStep(**item) for item in value.get("plan", [])]
        value["authorizations"] = [
            Authorization(**item) for item in value.get("authorizations", [])
        ]
        value["artifacts"] = [
            Artifact(**item) for item in value.get("artifacts", [])
        ]
        value["evidence"] = [
            Evidence(**item) for item in value.get("evidence", [])
        ]
        return cls(**value)
