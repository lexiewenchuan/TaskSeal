import unittest

from taskseal.models import AuthorizationRequest
from taskseal.policy import AuthorizationError, PolicyEngine

from test_state import make_work_item


class PolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = PolicyEngine()
        self.work_item = make_work_item()

    def test_rejects_action_outside_resource_scope(self) -> None:
        with self.assertRaises(AuthorizationError):
            self.policy.grant(
                self.work_item,
                AuthorizationRequest(
                    subject="agent",
                    resource_ids=["workspace"],
                    actions=["deploy"],
                ),
            )

    def test_delegation_cannot_expand_parent(self) -> None:
        parent = self.policy.grant(
            self.work_item,
            AuthorizationRequest(
                subject="main-agent",
                resource_ids=["workspace"],
                actions=["read"],
            ),
        )

        with self.assertRaises(AuthorizationError):
            self.policy.grant(
                self.work_item,
                AuthorizationRequest(
                    subject="child-agent",
                    resource_ids=["workspace"],
                    actions=["read", "write"],
                    parent_authorization_id=parent.id,
                ),
            )

    def test_require_binds_subject_resource_and_action(self) -> None:
        authorization = self.policy.grant(
            self.work_item,
            AuthorizationRequest(
                subject="agent",
                resource_ids=["workspace"],
                actions=["write"],
            ),
        )

        granted = self.policy.require(
            self.work_item,
            authorization_id=authorization.id,
            subject="agent",
            resource_id="workspace",
            action="write",
        )

        self.assertEqual(granted.id, authorization.id)
        with self.assertRaises(AuthorizationError):
            self.policy.require(
                self.work_item,
                authorization_id=authorization.id,
                subject="another-agent",
                resource_id="workspace",
                action="write",
            )


if __name__ == "__main__":
    unittest.main()
