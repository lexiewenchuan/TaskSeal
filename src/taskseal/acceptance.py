from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict, Iterable, Mapping, Protocol

from .models import Artifact, Evidence, WorkItem


class AcceptanceError(ValueError):
    pass


class EvidenceVerifier(Protocol):
    def verify(self, evidence: Evidence, artifact: Artifact) -> None:
        ...


class FileSha256EvidenceVerifier:
    """Re-checks local file evidence against the current external resource."""

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.resolve()

    def verify(self, evidence: Evidence, artifact: Artifact) -> None:
        path = (self.workspace / evidence.uri).resolve()
        try:
            path.relative_to(self.workspace)
        except ValueError as error:
            raise AcceptanceError(
                f"evidence path escapes workspace: {evidence.uri}"
            ) from error
        if not path.is_file():
            raise AcceptanceError(
                f"evidence resource does not exist: {evidence.uri}"
            )

        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        declared_digest = evidence.details.get("sha256")
        if digest != evidence.resource_revision:
            raise AcceptanceError(
                f"resource revision changed for evidence {evidence.id}"
            )
        if declared_digest != digest:
            raise AcceptanceError(
                f"evidence digest is invalid for {evidence.id}"
            )
        if artifact.uri != evidence.uri or artifact.revision != digest:
            raise AcceptanceError(
                f"artifact does not match evidence {evidence.id}"
            )
        declared_bytes = evidence.details.get("bytes")
        if declared_bytes != path.stat().st_size:
            raise AcceptanceError(
                f"evidence byte count is invalid for {evidence.id}"
            )


class Acceptor:
    """Accepts a task only when every criterion is supported by evidence."""

    def __init__(
        self,
        *,
        trusted_verifiers: Iterable[str],
        evidence_verifiers: Mapping[str, EvidenceVerifier],
    ) -> None:
        self.trusted_verifiers = {
            verifier for verifier in trusted_verifiers if verifier
        }
        if not self.trusted_verifiers:
            raise ValueError("at least one trusted verifier is required")
        self.evidence_verifiers = dict(evidence_verifiers)

    def verify(self, work_item: WorkItem, *, verifier: str) -> None:
        if verifier not in self.trusted_verifiers:
            raise AcceptanceError("verifier is not trusted")
        if verifier in work_item.executor_ids:
            raise AcceptanceError("an executor cannot be the independent verifier")

        evidence_by_id: Dict[str, Evidence] = {
            item.id: item for item in work_item.evidence
        }
        artifacts_by_revision = {
            (item.uri, item.revision): item for item in work_item.artifacts
        }
        failures = []
        verified_evidence = set()

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

            try:
                for evidence in attached:
                    if evidence.id in verified_evidence:
                        continue
                    artifact = artifacts_by_revision.get(
                        (evidence.uri, evidence.resource_revision)
                    )
                    if artifact is None:
                        raise AcceptanceError(
                            f"evidence {evidence.id} has no matching artifact"
                        )
                    evidence_verifier = self.evidence_verifiers.get(evidence.kind)
                    if evidence_verifier is None:
                        raise AcceptanceError(
                            f"no verifier is registered for evidence kind "
                            f"{evidence.kind}"
                        )
                    evidence_verifier.verify(evidence, artifact)
                    verified_evidence.add(evidence.id)
            except AcceptanceError as error:
                criterion.status = "failed"
                failures.append(f"{criterion.id}: {error}")
                continue

            criterion.status = "passed"
            criterion.verified_by = verifier

        if failures:
            raise AcceptanceError("; ".join(failures))
