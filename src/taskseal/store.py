from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import WorkItem, utc_now


class ConcurrentUpdateError(RuntimeError):
    pass


class SQLiteWorkItemStore:
    """Durable snapshots plus an append-only event trail."""

    def __init__(self, path: Path) -> None:
        self.path = path
        if str(path) != ":memory:":
            path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(path))
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self._migrate()

    def close(self) -> None:
        self.connection.close()

    def create(
        self,
        work_item: WorkItem,
        *,
        event_kind: str = "work_item.created",
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        work_item.validate(require_initial=True)
        with self.connection:
            exists = self.connection.execute(
                "SELECT 1 FROM work_items WHERE id = ?", (work_item.id,)
            ).fetchone()
            if exists is not None:
                raise ValueError(f"work item already exists: {work_item.id}")
            work_item.revision = 1
            work_item.updated_at = utc_now()
            self.connection.execute(
                """
                INSERT INTO work_items (id, revision, snapshot, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    work_item.id,
                    work_item.revision,
                    json.dumps(work_item.to_dict(), ensure_ascii=False),
                    work_item.updated_at,
                ),
            )
            self._append_event(work_item, event_kind, payload or {})

    def save(
        self,
        work_item: WorkItem,
        *,
        event_kind: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        work_item.validate()
        previous_revision = work_item.revision
        next_revision = previous_revision + 1
        work_item.updated_at = utc_now()
        snapshot = work_item.to_dict()
        snapshot["revision"] = next_revision

        with self.connection:
            cursor = self.connection.execute(
                """
                UPDATE work_items
                SET revision = ?, snapshot = ?, updated_at = ?
                WHERE id = ? AND revision = ?
                """,
                (
                    next_revision,
                    json.dumps(snapshot, ensure_ascii=False),
                    work_item.updated_at,
                    work_item.id,
                    previous_revision,
                ),
            )
            if cursor.rowcount != 1:
                raise ConcurrentUpdateError(
                    f"stale work item revision: {work_item.id}"
                )
            work_item.revision = next_revision
            self._append_event(work_item, event_kind, payload or {})

    def get(self, work_item_id: str) -> WorkItem:
        row = self.connection.execute(
            "SELECT snapshot FROM work_items WHERE id = ?", (work_item_id,)
        ).fetchone()
        if row is None:
            raise KeyError(work_item_id)
        return WorkItem.from_dict(json.loads(row["snapshot"]))

    def list_items(self) -> List[WorkItem]:
        rows = self.connection.execute(
            "SELECT snapshot FROM work_items ORDER BY updated_at DESC"
        ).fetchall()
        return [WorkItem.from_dict(json.loads(row["snapshot"])) for row in rows]

    def events(self, work_item_id: str) -> List[Dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT sequence, kind, payload, created_at, revision
            FROM events
            WHERE work_item_id = ?
            ORDER BY sequence
            """,
            (work_item_id,),
        ).fetchall()
        return [
            {
                "sequence": row["sequence"],
                "kind": row["kind"],
                "payload": json.loads(row["payload"]),
                "created_at": row["created_at"],
                "revision": row["revision"],
            }
            for row in rows
        ]

    def _append_event(
        self, work_item: WorkItem, kind: str, payload: Dict[str, Any]
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO events (
                work_item_id, revision, kind, payload, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                work_item.id,
                work_item.revision,
                kind,
                json.dumps(payload, ensure_ascii=False),
                utc_now(),
            ),
        )

    def _migrate(self) -> None:
        with self.connection:
            self.connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS work_items (
                    id TEXT PRIMARY KEY,
                    revision INTEGER NOT NULL,
                    snapshot TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    work_item_id TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    kind TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (work_item_id) REFERENCES work_items(id)
                );
                """
            )
