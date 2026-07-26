import unittest

from taskseal.models import AcceptanceCriterion, Resource, WorkItem, WorkStatus
from taskseal.state import InvalidTransition, transition


def make_work_item() -> WorkItem:
    return WorkItem.create(
        goal="test goal",
        requested_by="test-user",
        resources=[
            Resource(
                id="workspace",
                kind="local-directory",
                locator=".",
                allowed_actions=["read", "write"],
            )
        ],
        acceptance=[
            AcceptanceCriterion(
                id="done",
                statement="The result is verified.",
            )
        ],
    )


class StateMachineTests(unittest.TestCase):
    def test_valid_transition(self) -> None:
        work_item = make_work_item()

        transition(work_item, WorkStatus.PLANNING)

        self.assertEqual(work_item.status, WorkStatus.PLANNING)

    def test_invalid_transition_is_rejected(self) -> None:
        work_item = make_work_item()

        with self.assertRaises(InvalidTransition):
            transition(work_item, WorkStatus.ACCEPTED)


if __name__ == "__main__":
    unittest.main()
