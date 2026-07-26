from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Tuple
from uuid import uuid4

from .models import Artifact, Evidence, WorkItem
from .policy import PolicyEngine


class ResourceAccessError(PermissionError):
    pass


class LocalFileGateway:
    """The single side-effect boundary for a local filesystem workspace."""

    def __init__(self, workspace: Path, policy: PolicyEngine) -> None:
        self.workspace = workspace.resolve()
        self.policy = policy

    def read_text(
        self,
        work_item: WorkItem,
        *,
        authorization_id: str,
        subject: str,
        resource_id: str,
        relative_path: str,
    ) -> str:
        self.policy.require(
            work_item,
            authorization_id=authorization_id,
            subject=subject,
            resource_id=resource_id,
            action="read",
        )
        path = self._resolve_resource_path(work_item, resource_id, relative_path)
        return path.read_text(encoding="utf-8")

    def write_text(
        self,
        work_item: WorkItem,
        *,
        authorization_id: str,
        subject: str,
        resource_id: str,
        relative_path: str,
        content: str,
        supports: list[str],
    ) -> Tuple[Artifact, Evidence]:
        self.policy.require(
            work_item,
            authorization_id=authorization_id,
            subject=subject,
            resource_id=resource_id,
            action="write",
        )
        path = self._resolve_resource_path(work_item, resource_id, relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        uri = path.relative_to(self.workspace).as_posix()
        artifact = Artifact(
            id=f"artifact-{uuid4().hex[:12]}",
            kind="file",
            uri=uri,
            revision=digest,
            produced_by=subject,
        )
        evidence = Evidence(
            id=f"evidence-{uuid4().hex[:12]}",
            kind="file-sha256",
            uri=uri,
            supports=list(supports),
            resource_revision=digest,
            collected_by="local-file-gateway",
            details={"sha256": digest, "bytes": path.stat().st_size},
        )
        return artifact, evidence

    def _resolve_resource_path(
        self, work_item: WorkItem, resource_id: str, relative_path: str
    ) -> Path:
        resource = next(
            (item for item in work_item.resources if item.id == resource_id),
            None,
        )
        if resource is None:
            raise ResourceAccessError("resource is outside task scope")
        if resource.kind != "local-directory":
            raise ResourceAccessError(
                f"local gateway cannot handle resource kind {resource.kind}"
            )

        resource_root = (self.workspace / resource.locator).resolve()
        candidate = (resource_root / relative_path).resolve()
        if not self._is_within(resource_root, candidate):
            raise ResourceAccessError("path escapes the authorized resource")
        if not self._is_within(self.workspace, candidate):
            raise ResourceAccessError("path escapes the configured workspace")
        return candidate

    @staticmethod
    def _is_within(parent: Path, candidate: Path) -> bool:
        try:
            candidate.relative_to(parent)
        except ValueError:
            return False
        return True
