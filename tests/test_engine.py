import tempfile
import unittest
from pathlib import Path

from taskseal.acceptance import AcceptanceError
from taskseal.engine import TaskSealEngine
from taskseal.gateway import LocalFileGateway
from taskseal.models import AuthorizationRequest, PlanStep, WorkStatus
from taskseal.policy import PolicyEngine
from taskseal.store import SQLiteWorkItemStore

from test_state import make_work_item


class EngineIntegrationTests(unittest.TestCase):
    def test_authorized_task_is_persisted_and_independently_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = SQLiteWorkItemStore(root / "taskseal.db")
            policy = PolicyEngine()
            engine = TaskSealEngine(store, policy=policy)
            work_item = make_work_item()

            engine.create(work_item)
            engine.set_plan(
                work_item,
                [PlanStep(id="write", summary="Write verified result")],
            )
            engine.request_authorization(work_item)
            authorization = engine.grant(
                work_item,
                AuthorizationRequest(
                    subject="executor",
                    resource_ids=["workspace"],
                    actions=["write"],
                ),
            )
            engine.start(work_item, executor="executor")
            artifact, evidence = LocalFileGateway(root, policy).write_text(
                work_item,
                authorization_id=authorization.id,
                subject="executor",
                resource_id="workspace",
                relative_path="result.txt",
                content="done\n",
                supports=["done"],
            )
            engine.attach_result(
                work_item, artifact=artifact, evidence=evidence
            )
            engine.begin_verification(work_item)
            engine.accept(work_item, verifier="independent-verifier")

            restored = store.get(work_item.id)
            events = store.events(work_item.id)
            store.close()

            self.assertEqual(restored.status, WorkStatus.ACCEPTED)
            self.assertEqual(restored.acceptance[0].status, "passed")
            self.assertEqual(
                restored.acceptance[0].verified_by,
                "independent-verifier",
            )
            self.assertEqual(restored.plan[0].status, "completed")
            self.assertEqual(events[-1]["kind"], "work_item.accepted")
            self.assertGreaterEqual(restored.revision, 7)

    def test_execution_requires_authorization_for_that_executor(self) -> None:
        work_item = make_work_item()

        with tempfile.TemporaryDirectory() as directory:
            store = SQLiteWorkItemStore(Path(directory) / "taskseal.db")
            engine = TaskSealEngine(store)
            engine.create(work_item)
            engine.set_plan(
                work_item,
                [PlanStep(id="write", summary="Write verified result")],
            )
            engine.request_authorization(work_item)
            engine.grant(
                work_item,
                AuthorizationRequest(
                    subject="another-agent",
                    resource_ids=["workspace"],
                    actions=["write"],
                ),
            )

            with self.assertRaisesRegex(
                ValueError, "executor has no active authorization"
            ):
                engine.start(work_item, executor="executor")

            self.assertEqual(work_item.status, WorkStatus.AUTHORIZED)
            store.close()

    def test_executor_cannot_accept_its_own_work(self) -> None:
        work_item = make_work_item()
        work_item.status = WorkStatus.VERIFYING
        work_item.executor_ids = ["executor"]

        with tempfile.TemporaryDirectory() as directory:
            store = SQLiteWorkItemStore(Path(directory) / "taskseal.db")
            engine = TaskSealEngine(store)
            engine.create(work_item)

            with self.assertRaises(AcceptanceError):
                engine.accept(work_item, verifier="executor")

            self.assertEqual(work_item.status, WorkStatus.REPAIRING)
            store.close()


if __name__ == "__main__":
    unittest.main()
