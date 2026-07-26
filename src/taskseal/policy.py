from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Optional
from uuid import uuid4

from .models import Authorization, AuthorizationRequest, WorkItem


class AuthorizationError(PermissionError):
    pass


class PolicyEngine:
    """Issues and checks resource-scoped, non-expanding authorizations."""

    def grant(
        self, work_item: WorkItem, request: AuthorizationRequest
    ) -> Authorization:
        resources = {resource.id: resource for resource in work_item.resources}
        missing = sorted(set(request.resource_ids) - set(resources))
        if missing:
            raise AuthorizationError(f"resources are outside task scope: {missing}")

        prohibited = sorted(set(request.actions) & set(work_item.prohibited_actions))
        if prohibited:
            raise AuthorizationError(f"actions are prohibited: {prohibited}")

        for resource_id in request.resource_ids:
            resource = resources[resource_id]
            extra = sorted(set(request.actions) - set(resource.allowed_actions))
            if extra:
                raise AuthorizationError(
                    f"actions are not allowed for {resource_id}: {extra}"
                )

        parent = self._find_parent(work_item, request.parent_authorization_id)
        if parent is not None:
            self._require_subset(request, parent)

        if request.expires_at is not None:
            expiry = datetime.fromisoformat(request.expires_at)
            if expiry.tzinfo is None:
                raise AuthorizationError("expires_at must include a timezone")
            if expiry <= datetime.now(timezone.utc):
                raise AuthorizationError("authorization is already expired")

        authorization = Authorization(
            id=f"auth-{uuid4().hex[:12]}",
            subject=request.subject,
            resource_ids=list(request.resource_ids),
            actions=list(request.actions),
            conditions=list(request.conditions),
            expires_at=request.expires_at,
            parent_authorization_id=request.parent_authorization_id,
        )
        work_item.authorizations.append(authorization)
        return authorization

    def require(
        self,
        work_item: WorkItem,
        *,
        authorization_id: str,
        subject: str,
        resource_id: str,
        action: str,
    ) -> Authorization:
        authorization = next(
            (
                candidate
                for candidate in work_item.authorizations
                if candidate.id == authorization_id
            ),
            None,
        )
        if authorization is None:
            raise AuthorizationError("authorization does not exist")
        if authorization.status != "granted":
            raise AuthorizationError("authorization is not active")
        if authorization.subject != subject:
            raise AuthorizationError("authorization belongs to another subject")
        if resource_id not in authorization.resource_ids:
            raise AuthorizationError("resource is outside authorization")
        if action not in authorization.actions:
            raise AuthorizationError("action is outside authorization")
        if authorization.expires_at is not None:
            expiry = datetime.fromisoformat(authorization.expires_at)
            if expiry <= datetime.now(timezone.utc):
                authorization.status = "expired"
                raise AuthorizationError("authorization has expired")
        return authorization

    @staticmethod
    def _find_parent(
        work_item: WorkItem, parent_id: Optional[str]
    ) -> Optional[Authorization]:
        if parent_id is None:
            return None
        parent = next(
            (item for item in work_item.authorizations if item.id == parent_id),
            None,
        )
        if parent is None or parent.status != "granted":
            raise AuthorizationError("parent authorization is not active")
        return parent

    @staticmethod
    def _require_subset(
        request: AuthorizationRequest, parent: Authorization
    ) -> None:
        if not set(request.resource_ids).issubset(parent.resource_ids):
            raise AuthorizationError("delegation expands resource scope")
        if not set(request.actions).issubset(parent.actions):
            raise AuthorizationError("delegation expands action scope")
        if parent.expires_at is not None:
            if request.expires_at is None:
                raise AuthorizationError("delegation removes parent expiry")
            if datetime.fromisoformat(request.expires_at) > datetime.fromisoformat(
                parent.expires_at
            ):
                raise AuthorizationError("delegation extends parent expiry")
