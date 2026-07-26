"""TaskSeal: a task-first control plane for trustworthy agent work."""

from .acceptance import AcceptanceError, Acceptor
from .engine import TaskSealEngine
from .gateway import LocalFileGateway, ResourceAccessError
from .models import (
    AcceptanceCriterion,
    Artifact,
    Authorization,
    AuthorizationRequest,
    Evidence,
    Resource,
    RiskLevel,
    WorkItem,
    WorkStatus,
)
from .policy import AuthorizationError, PolicyEngine
from .store import SQLiteWorkItemStore

__all__ = [
    "AcceptanceCriterion",
    "AcceptanceError",
    "Acceptor",
    "Artifact",
    "Authorization",
    "AuthorizationError",
    "AuthorizationRequest",
    "Evidence",
    "LocalFileGateway",
    "PolicyEngine",
    "Resource",
    "ResourceAccessError",
    "RiskLevel",
    "SQLiteWorkItemStore",
    "TaskSealEngine",
    "WorkItem",
    "WorkStatus",
]

__version__ = "0.1.0"
