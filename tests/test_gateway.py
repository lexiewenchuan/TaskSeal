import tempfile
import unittest
from pathlib import Path

from taskseal.gateway import LocalFileGateway, ResourceAccessError
from taskseal.models import AuthorizationRequest
from taskseal.policy import PolicyEngine

from test_state import make_work_item


class GatewayTests(unittest.TestCase):
    def test_write_produces_revision_bound_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            policy = PolicyEngine(trusted_authorizers={"owner"})
            work_item = make_work_item()
            authorization = policy.grant(
                work_item,
                AuthorizationRequest(
                    subject="agent",
                    resource_ids=["workspace"],
                    actions=["write"],
                ),
                granted_by="owner",
            )
            gateway = LocalFileGateway(workspace, policy)

            artifact, evidence = gateway.write_text(
                work_item,
                authorization_id=authorization.id,
                subject="agent",
                resource_id="workspace",
                relative_path="result.txt",
                content="verified result\n",
                supports=["done"],
            )

            self.assertEqual(
                (workspace / "result.txt").read_text(encoding="utf-8"),
                "verified result\n",
            )
            self.assertEqual(artifact.revision, evidence.resource_revision)
            self.assertEqual(evidence.kind, "file-sha256")
            self.assertEqual(evidence.supports, ["done"])

    def test_path_escape_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            policy = PolicyEngine(trusted_authorizers={"owner"})
            work_item = make_work_item()
            authorization = policy.grant(
                work_item,
                AuthorizationRequest(
                    subject="agent",
                    resource_ids=["workspace"],
                    actions=["write"],
                ),
                granted_by="owner",
            )
            gateway = LocalFileGateway(workspace, policy)

            with self.assertRaises(ResourceAccessError):
                gateway.write_text(
                    work_item,
                    authorization_id=authorization.id,
                    subject="agent",
                    resource_id="workspace",
                    relative_path="../outside.txt",
                    content="not allowed",
                    supports=["done"],
                )


if __name__ == "__main__":
    unittest.main()
