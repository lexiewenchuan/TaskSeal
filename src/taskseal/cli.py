from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional, Sequence

from .acceptance import Acceptor, FileSha256EvidenceVerifier
from .engine import TaskSealEngine
from .gateway import LocalFileGateway
from .models import (
    AcceptanceCriterion,
    AuthorizationRequest,
    PlanStep,
    Resource,
    WorkItem,
)
from .policy import PolicyEngine
from .store import SQLiteWorkItemStore


def _store(path: str) -> SQLiteWorkItemStore:
    return SQLiteWorkItemStore(Path(path))


def run_demo(workspace: Path, database: Path) -> WorkItem:
    workspace.mkdir(parents=True, exist_ok=True)
    store = SQLiteWorkItemStore(database)
    policy = PolicyEngine(trusted_authorizers={"demo-owner"})
    acceptor = Acceptor(
        trusted_verifiers={"demo-verifier"},
        evidence_verifiers={
            "file-sha256": FileSha256EvidenceVerifier(workspace)
        },
    )
    engine = TaskSealEngine(store, policy=policy, acceptor=acceptor)

    work_item = WorkItem.create(
        goal="Create a verified TaskSeal demo result.",
        requested_by="cli-user",
        resources=[
            Resource(
                id="demo-workspace",
                kind="local-directory",
                locator=".",
                allowed_actions=["read", "write"],
            )
        ],
        acceptance=[
            AcceptanceCriterion(
                id="result-created",
                statement="The result file exists and is bound to a SHA-256 digest.",
                required_evidence_kinds=["file-sha256"],
            )
        ],
        prohibited_actions=["network", "deploy", "delete"],
    )
    engine.create(work_item)
    engine.set_plan(
        work_item,
        [
            PlanStep(
                id="write-result",
                summary="Write a result through the authorized resource gateway.",
                executor="demo-agent",
            ),
        ],
    )
    engine.request_authorization(work_item)
    authorization = engine.grant(
        work_item,
        AuthorizationRequest(
            subject="demo-agent",
            resource_ids=["demo-workspace"],
            actions=["read", "write"],
        ),
        granted_by="demo-owner",
    )
    engine.start(work_item, executor="demo-agent")

    gateway = LocalFileGateway(workspace, policy)
    artifact, evidence = gateway.write_text(
        work_item,
        authorization_id=authorization.id,
        subject="demo-agent",
        resource_id="demo-workspace",
        relative_path="taskseal-result.txt",
        content="TaskSeal completed this work through an authorized gateway.\n",
        supports=["result-created"],
    )
    engine.attach_result(work_item, artifact=artifact, evidence=evidence)
    engine.complete_step(
        work_item, step_id="write-result", executor="demo-agent"
    )
    engine.begin_verification(work_item)
    engine.accept(work_item, verifier="demo-verifier")
    store.close()
    return work_item


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="taskseal",
        description="A task-first control plane for trustworthy agent work.",
    )
    parser.add_argument(
        "--database",
        default=".taskseal/taskseal.db",
        help="SQLite state database (default: .taskseal/taskseal.db)",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    demo = subcommands.add_parser(
        "demo", help="run one authorized, evidence-backed local task"
    )
    demo.add_argument(
        "--workspace",
        default=".taskseal/demo-workspace",
        help="directory the demo is allowed to modify",
    )

    show = subcommands.add_parser("show", help="print one durable work item")
    show.add_argument("work_item_id")

    subcommands.add_parser("list", help="list durable work items")

    events = subcommands.add_parser(
        "events", help="print the event trail for one work item"
    )
    events.add_argument("work_item_id")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "demo":
        work_item = run_demo(Path(args.workspace), Path(args.database))
        print(json.dumps(work_item.to_dict(), ensure_ascii=False, indent=2))
        return 0

    store = _store(args.database)
    try:
        if args.command == "show":
            print(
                json.dumps(
                    store.get(args.work_item_id).to_dict(),
                    ensure_ascii=False,
                    indent=2,
                )
            )
        elif args.command == "list":
            summary = [
                {
                    "id": item.id,
                    "status": item.status.value,
                    "goal": item.goal,
                    "revision": item.revision,
                }
                for item in store.list_items()
            ]
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        elif args.command == "events":
            print(
                json.dumps(
                    store.events(args.work_item_id),
                    ensure_ascii=False,
                    indent=2,
                )
            )
    finally:
        store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
