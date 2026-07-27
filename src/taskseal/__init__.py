"""TaskSeal: a task-first control plane for trustworthy agent work."""

from .acceptance import (
    AcceptanceError,
    Acceptor,
    EvidenceVerifier,
    FileSha256EvidenceVerifier,
)
from .engine import TaskSealEngine
from .gateway import LocalFileGateway, ResourceAccessError
from .models import (
    AcceptanceCriterion,
    Artifact,
    Authorization,
    AuthorizationRequest,
    Evidence,
    PlanStep,
    Resource,
    RiskLevel,
    SCHEMA_VERSION,
    WorkItem,
    WorkStatus,
    WorkItemValidationError,
)
from .policy import AuthorizationError, PolicyEngine
from .state import InvalidTransition
from .store import ConcurrentUpdateError, SQLiteWorkItemStore

__all__ = [
    "AcceptanceCriterion",
    "AcceptanceError",
    "Acceptor",
    "Artifact",
    "Authorization",
    "AuthorizationError",
    "AuthorizationRequest",
    "ConcurrentUpdateError",
    "Evidence",
    "EvidenceVerifier",
    "FileSha256EvidenceVerifier",
    "LocalFileGateway",
    "InvalidTransition",
    "PlanStep",
    "PolicyEngine",
    "Resource",
    "ResourceAccessError",
    "RiskLevel",
    "SCHEMA_VERSION",
    "SQLiteWorkItemStore",
    "TaskSealEngine",
    "WorkItem",
    "WorkStatus",
    "WorkItemValidationError",
]

__version__ = "0.1.1"
