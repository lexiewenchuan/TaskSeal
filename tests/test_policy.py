import unittest

from taskseal.models import AuthorizationRequest
from taskseal.policy import AuthorizationError, PolicyEngine

from test_state import make_work_item


class PolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = PolicyEngine(trusted_authorizers={"owner"})
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
                granted_by="owner",
            )

    def test_delegation_cannot_expand_parent(self) -> None:
        parent = self.policy.grant(
            self.work_item,
            AuthorizationRequest(
                subject="main-agent",
                resource_ids=["workspace"],
                actions=["read"],
            ),
            granted_by="owner",
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
                granted_by="main-agent",
            )

    def test_require_binds_subject_resource_and_action(self) -> None:
        authorization = self.policy.grant(
            self.work_item,
            AuthorizationRequest(
                subject="agent",
                resource_ids=["workspace"],
                actions=["write"],
            ),
            granted_by="owner",
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

    def test_subject_cannot_authorize_itself(self) -> None:
        with self.assertRaisesRegex(
            AuthorizationError, "cannot authorize itself"
        ):
            self.policy.grant(
                self.work_item,
                AuthorizationRequest(
                    subject="owner",
                    resource_ids=["workspace"],
                    actions=["write"],
                ),
                granted_by="owner",
            )

    def test_untrusted_root_authorizer_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            AuthorizationError, "not a trusted authorizer"
        ):
            self.policy.grant(
                self.work_item,
                AuthorizationRequest(
                    subject="agent",
                    resource_ids=["workspace"],
                    actions=["write"],
                ),
                granted_by="unknown",
            )

    def test_zulu_expiry_is_supported_on_python_39(self) -> None:
        authorization = self.policy.grant(
            self.work_item,
            AuthorizationRequest(
                subject="agent",
                resource_ids=["workspace"],
                actions=["write"],
                expires_at="2099-01-01T00:00:00Z",
            ),
            granted_by="owner",
        )

        self.assertEqual(authorization.expires_at, "2099-01-01T00:00:00Z")

    def test_unimplemented_conditions_fail_closed(self) -> None:
        with self.assertRaisesRegex(
            AuthorizationError, "conditions are not supported"
        ):
            self.policy.grant(
                self.work_item,
                AuthorizationRequest(
                    subject="agent",
                    resource_ids=["workspace"],
                    actions=["write"],
                    conditions=["must be approved"],
                ),
                granted_by="owner",
            )

    def test_trusted_authorizer_can_revoke_a_grant(self) -> None:
        authorization = self.policy.grant(
            self.work_item,
            AuthorizationRequest(
                subject="agent",
                resource_ids=["workspace"],
                actions=["write"],
            ),
            granted_by="owner",
        )

        self.policy.revoke(
            self.work_item,
            authorization_id=authorization.id,
            revoked_by="owner",
        )

        self.assertEqual(authorization.status, "revoked")
        with self.assertRaisesRegex(AuthorizationError, "not active"):
            self.policy.require(
                self.work_item,
                authorization_id=authorization.id,
                subject="agent",
                resource_id="workspace",
                action="write",
            )


if __name__ == "__main__":
    unittest.main()
