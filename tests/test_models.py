import json
import tempfile
import unittest
from pathlib import Path

from taskseal.models import (
    AcceptanceCriterion,
    Resource,
    WorkItem,
    WorkItemValidationError,
    WorkStatus,
)
from taskseal.store import SQLiteWorkItemStore


class WorkItemValidationTests(unittest.TestCase):
    def test_acceptance_is_required(self) -> None:
        work_item = WorkItem.create(
            goal="test",
            requested_by="user",
            resources=[],
            acceptance=[],
        )

        with self.assertRaisesRegex(
            WorkItemValidationError, "acceptance criterion"
        ):
            work_item.validate()

    def test_new_work_item_must_start_in_draft(self) -> None:
        work_item = WorkItem.create(
            goal="test",
            requested_by="user",
            resources=[],
            acceptance=[
                AcceptanceCriterion(id="done", statement="Done")
            ],
        )
        work_item.status = WorkStatus.ACCEPTED

        with tempfile.TemporaryDirectory() as directory:
            store = SQLiteWorkItemStore(Path(directory) / "taskseal.db")
            with self.assertRaisesRegex(
                WorkItemValidationError, "start in draft"
            ):
                store.create(work_item)
            store.close()

    def test_serialized_work_item_round_trips(self) -> None:
        work_item = WorkItem.create(
            goal="test",
            requested_by="user",
            resources=[
                Resource(
                    id="workspace",
                    kind="local-directory",
                    locator=".",
                    allowed_actions=["read"],
                )
            ],
            acceptance=[
                AcceptanceCriterion(id="done", statement="Done")
            ],
        )

        restored = WorkItem.from_dict(work_item.to_dict())

        self.assertEqual(restored.to_dict(), work_item.to_dict())
        self.assertEqual(restored.schema_version, "0.1")

    def test_public_example_loads_as_runtime_model(self) -> None:
        example = (
            Path(__file__).resolve().parents[1]
            / "examples"
            / "software-change"
            / "work-item.json"
        )

        work_item = WorkItem.from_dict(
            json.loads(example.read_text(encoding="utf-8"))
        )

        self.assertEqual(work_item.status, WorkStatus.ACCEPTED)
        self.assertEqual(work_item.schema_version, "0.1")

    def test_legacy_grant_is_loaded_as_revoked(self) -> None:
        work_item = WorkItem.create(
            goal="legacy",
            requested_by="user",
            resources=[
                Resource(
                    id="workspace",
                    kind="local-directory",
                    locator=".",
                    allowed_actions=["read"],
                )
            ],
            acceptance=[
                AcceptanceCriterion(id="done", statement="Done")
            ],
        )
        payload = work_item.to_dict()
        payload.pop("schema_version")
        payload["authorizations"] = [
            {
                "id": "legacy-grant",
                "subject": "agent",
                "resource_ids": ["workspace"],
                "actions": ["read"],
                "conditions": ["unenforced legacy condition"],
                "expires_at": None,
                "status": "granted",
                "parent_authorization_id": None,
                "granted_at": "2026-07-26T08:00:00Z",
            }
        ]

        restored = WorkItem.from_dict(payload)

        self.assertEqual(restored.authorizations[0].status, "revoked")
        self.assertEqual(
            restored.authorizations[0].granted_by, "legacy-unverified"
        )


if __name__ == "__main__":
    unittest.main()
