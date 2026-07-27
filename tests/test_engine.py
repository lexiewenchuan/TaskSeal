import tempfile
import unittest
from pathlib import Path

from taskseal.acceptance import (
    AcceptanceError,
    Acceptor,
    FileSha256EvidenceVerifier,
)
from taskseal.engine import TaskSealEngine
from taskseal.gateway import LocalFileGateway
from taskseal.models import (
    Artifact,
    AuthorizationRequest,
    Evidence,
    PlanStep,
    WorkStatus,
)
from taskseal.policy import PolicyEngine
from taskseal.store import SQLiteWorkItemStore

from test_state import make_work_item


class EngineIntegrationTests(unittest.TestCase):
    @staticmethod
    def make_engine(
        root: Path,
        *,
        trusted_verifiers: set[str] = {"independent-verifier"},
    ) -> tuple[SQLiteWorkItemStore, PolicyEngine, TaskSealEngine]:
        store = SQLiteWorkItemStore(root / "taskseal.db")
        policy = PolicyEngine(trusted_authorizers={"owner"})
        acceptor = Acceptor(
            trusted_verifiers=trusted_verifiers,
            evidence_verifiers={
                "file-sha256": FileSha256EvidenceVerifier(root)
            },
        )
        return (
            store,
            policy,
            TaskSealEngine(store, policy=policy, acceptor=acceptor),
        )

    def test_authorized_task_is_persisted_and_independently_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store, policy, engine = self.make_engine(root)
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
                granted_by="owner",
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
            engine.complete_step(
                work_item, step_id="write", executor="executor"
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
            root = Path(directory)
            store, _, engine = self.make_engine(root)
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
                granted_by="owner",
            )

            with self.assertRaisesRegex(
                ValueError, "executor has no active authorization"
            ):
                engine.start(work_item, executor="executor")

            self.assertEqual(work_item.status, WorkStatus.AUTHORIZED)
            store.close()

    def test_revoked_authorization_blocks_execution_and_is_audited(self) -> None:
        work_item = make_work_item()

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store, _, engine = self.make_engine(root)
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
                granted_by="owner",
            )
            engine.revoke_authorization(
                work_item,
                authorization_id=authorization.id,
                revoked_by="owner",
            )

            with self.assertRaisesRegex(
                ValueError, "no active authorization"
            ):
                engine.start(work_item, executor="executor")

            self.assertEqual(
                store.events(work_item.id)[-1]["kind"],
                "authorization.revoked",
            )
            store.close()

    def test_executor_cannot_accept_its_own_work(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store, policy, engine = self.make_engine(
                root, trusted_verifiers={"executor"}
            )
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
                granted_by="owner",
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
            engine.complete_step(
                work_item, step_id="write", executor="executor"
            )
            engine.begin_verification(work_item)

            with self.assertRaises(AcceptanceError):
                engine.accept(work_item, verifier="executor")

            self.assertEqual(work_item.status, WorkStatus.REPAIRING)
            store.close()

    def test_fabricated_file_evidence_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store, _, engine = self.make_engine(root)
            work_item = make_work_item()
            engine.create(work_item)
            engine.set_plan(
                work_item,
                [PlanStep(id="write", summary="Write verified result")],
            )
            engine.request_authorization(work_item)
            engine.grant(
                work_item,
                AuthorizationRequest(
                    subject="executor",
                    resource_ids=["workspace"],
                    actions=["write"],
                ),
                granted_by="owner",
            )
            engine.start(work_item, executor="executor")
            engine.attach_result(
                work_item,
                artifact=Artifact(
                    id="artifact",
                    kind="file",
                    uri="missing.txt",
                    revision="made-up",
                    produced_by="executor",
                ),
                evidence=Evidence(
                    id="evidence",
                    kind="file-sha256",
                    uri="missing.txt",
                    supports=["done"],
                    resource_revision="made-up",
                    collected_by="untrusted",
                    details={"sha256": "made-up"},
                ),
            )
            engine.complete_step(
                work_item, step_id="write", executor="executor"
            )
            engine.begin_verification(work_item)

            with self.assertRaisesRegex(
                AcceptanceError, "resource does not exist"
            ):
                engine.accept(
                    work_item, verifier="independent-verifier"
                )

            self.assertEqual(work_item.status, WorkStatus.REPAIRING)
            store.close()

    def test_failed_verification_can_be_replanned(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store, _, engine = self.make_engine(root)
            work_item = make_work_item()
            engine.create(work_item)
            engine.set_plan(
                work_item,
                [PlanStep(id="write", summary="Write fabricated result")],
            )
            engine.request_authorization(work_item)
            engine.grant(
                work_item,
                AuthorizationRequest(
                    subject="executor",
                    resource_ids=["workspace"],
                    actions=["write"],
                ),
                granted_by="owner",
            )
            engine.start(work_item, executor="executor")
            engine.attach_result(
                work_item,
                artifact=Artifact(
                    id="artifact",
                    kind="file",
                    uri="missing.txt",
                    revision="made-up",
                    produced_by="executor",
                ),
                evidence=Evidence(
                    id="evidence",
                    kind="file-sha256",
                    uri="missing.txt",
                    supports=["done"],
                    resource_revision="made-up",
                    collected_by="untrusted",
                    details={"sha256": "made-up"},
                ),
            )
            engine.complete_step(
                work_item, step_id="write", executor="executor"
            )
            engine.begin_verification(work_item)
            with self.assertRaises(AcceptanceError):
                engine.accept(
                    work_item, verifier="independent-verifier"
                )

            engine.set_plan(
                work_item,
                [PlanStep(id="repair", summary="Repair result")],
            )

            self.assertEqual(work_item.status, WorkStatus.PLANNING)
            self.assertEqual(work_item.plan[0].id, "repair")
            store.close()

    def test_changed_file_invalidates_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store, policy, engine = self.make_engine(root)
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
                granted_by="owner",
            )
            engine.start(work_item, executor="executor")
            artifact, evidence = LocalFileGateway(root, policy).write_text(
                work_item,
                authorization_id=authorization.id,
                subject="executor",
                resource_id="workspace",
                relative_path="result.txt",
                content="original\n",
                supports=["done"],
            )
            engine.attach_result(
                work_item, artifact=artifact, evidence=evidence
            )
            engine.complete_step(
                work_item, step_id="write", executor="executor"
            )
            (root / "result.txt").write_text("tampered\n", encoding="utf-8")
            engine.begin_verification(work_item)

            with self.assertRaisesRegex(
                AcceptanceError, "resource revision changed"
            ):
                engine.accept(
                    work_item, verifier="independent-verifier"
                )

            self.assertEqual(work_item.status, WorkStatus.REPAIRING)
            store.close()


if __name__ == "__main__":
    unittest.main()
