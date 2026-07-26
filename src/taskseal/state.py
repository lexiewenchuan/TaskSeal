from __future__ import annotations

from typing import Dict, Set

from .models import WorkItem, WorkStatus, utc_now


class InvalidTransition(ValueError):
    pass


ALLOWED_TRANSITIONS: Dict[WorkStatus, Set[WorkStatus]] = {
    WorkStatus.DRAFT: {WorkStatus.PLANNING, WorkStatus.CANCELLED},
    WorkStatus.PLANNING: {
        WorkStatus.AWAITING_AUTHORIZATION,
        WorkStatus.BLOCKED,
        WorkStatus.CANCELLED,
    },
    WorkStatus.AWAITING_AUTHORIZATION: {
        WorkStatus.AUTHORIZED,
        WorkStatus.BLOCKED,
        WorkStatus.CANCELLED,
    },
    WorkStatus.AUTHORIZED: {
        WorkStatus.EXECUTING,
        WorkStatus.BLOCKED,
        WorkStatus.CANCELLED,
    },
    WorkStatus.EXECUTING: {
        WorkStatus.VERIFYING,
        WorkStatus.REPAIRING,
        WorkStatus.BLOCKED,
        WorkStatus.CANCELLED,
    },
    WorkStatus.VERIFYING: {
        WorkStatus.ACCEPTED,
        WorkStatus.REPAIRING,
        WorkStatus.BLOCKED,
    },
    WorkStatus.REPAIRING: {
        WorkStatus.PLANNING,
        WorkStatus.BLOCKED,
        WorkStatus.CANCELLED,
    },
    WorkStatus.BLOCKED: {
        WorkStatus.PLANNING,
        WorkStatus.CANCELLED,
    },
    WorkStatus.ACCEPTED: set(),
    WorkStatus.CANCELLED: set(),
}


def transition(work_item: WorkItem, target: WorkStatus) -> None:
    allowed = ALLOWED_TRANSITIONS[work_item.status]
    if target not in allowed:
        raise InvalidTransition(
            f"cannot transition {work_item.id} from "
            f"{work_item.status.value} to {target.value}"
        )
    work_item.status = target
    work_item.updated_at = utc_now()
