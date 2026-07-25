"""Corporate Artifacts Repository for Central Knowledge Graph indexing.

Manages indexing, metadata storage, and retrieval for uploaded files
tagged by creator_role, shadow_task_id, and SHA-256 content hashes.
"""

from __future__ import annotations

import json

import aiosqlite
from loguru import logger

from shadow_adapter.models import CorporateArtifact


class CorporateArtifactsRepository:
    """Repository managing corporate_artifacts table in shadow_tasks.db."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    async def initialize(self) -> None:
        """Initialize SQLite database table for corporate_artifacts."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS corporate_artifacts (
                    id TEXT PRIMARY KEY,
                    shadow_task_id TEXT NOT NULL,
                    opc_task_id TEXT NOT NULL,
                    opc_work_item_id TEXT,
                    creator_role TEXT NOT NULL,
                    creator_contractor_id TEXT,
                    original_filename TEXT NOT NULL,
                    storage_path TEXT NOT NULL,
                    file_size_bytes INTEGER NOT NULL,
                    mime_type TEXT NOT NULL DEFAULT 'application/octet-stream',
                    sha256_hash TEXT NOT NULL,
                    tags_json TEXT DEFAULT '[]',
                    metadata_json TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_corp_art_task ON corporate_artifacts(shadow_task_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_corp_art_role ON corporate_artifacts(creator_role)")
            await db.commit()

    def _row_to_artifact(self, row: aiosqlite.Row | tuple) -> CorporateArtifact:
        if isinstance(row, aiosqlite.Row):
            data = dict(row)
        else:
            fields = [
                "id",
                "shadow_task_id",
                "opc_task_id",
                "opc_work_item_id",
                "creator_role",
                "creator_contractor_id",
                "original_filename",
                "storage_path",
                "file_size_bytes",
                "mime_type",
                "sha256_hash",
                "tags_json",
                "metadata_json",
                "created_at",
            ]
            data = dict(zip(fields, row, strict=False))

        tags = json.loads(data.get("tags_json") or "[]")
        metadata = json.loads(data.get("metadata_json") or "{}")

        art_id = str(data["id"])
        return CorporateArtifact(
            id=art_id,
            shadow_task_id=str(data["shadow_task_id"]),
            opc_task_id=str(data["opc_task_id"]),
            opc_work_item_id=data.get("opc_work_item_id"),
            creator_role=str(data["creator_role"]),
            creator_contractor_id=data.get("creator_contractor_id"),
            original_filename=str(data["original_filename"]),
            storage_path=str(data["storage_path"]),
            file_size_bytes=int(data["file_size_bytes"]),
            mime_type=str(data.get("mime_type", "application/octet-stream")),
            sha256_hash=str(data["sha256_hash"]),
            tags=tags,
            metadata=metadata,
            download_url=f"/api/v1/artifacts/{art_id}/download",
            created_at=str(data.get("created_at")) if data.get("created_at") else None,
        )

    async def create_artifact(self, artifact: CorporateArtifact) -> CorporateArtifact:
        """Index a new Corporate Artifact record."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO corporate_artifacts (
                    id, shadow_task_id, opc_task_id, opc_work_item_id,
                    creator_role, creator_contractor_id, original_filename,
                    storage_path, file_size_bytes, mime_type, sha256_hash,
                    tags_json, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    artifact.id,
                    artifact.shadow_task_id,
                    artifact.opc_task_id,
                    artifact.opc_work_item_id,
                    artifact.creator_role,
                    artifact.creator_contractor_id,
                    artifact.original_filename,
                    artifact.storage_path,
                    artifact.file_size_bytes,
                    artifact.mime_type,
                    artifact.sha256_hash,
                    json.dumps(artifact.tags),
                    json.dumps(artifact.metadata),
                ),
            )
            await db.commit()
            logger.info(
                f"[CorporateArtifactsRepository] Indexed artifact '{artifact.original_filename}' "
                f"(id={artifact.id}, role={artifact.creator_role})"
            )
            return await self.get_artifact(artifact.id) or artifact

    async def get_artifact(self, artifact_id: str) -> CorporateArtifact | None:
        """Fetch an artifact record by unique ID."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM corporate_artifacts WHERE id = ?", (artifact_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return self._row_to_artifact(row)
                return None

    async def list_artifacts_for_task(self, shadow_task_id: str) -> list[CorporateArtifact]:
        """List all corporate artifacts attached to a specific shadow task."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM corporate_artifacts WHERE shadow_task_id = ? ORDER BY created_at ASC",
                (shadow_task_id,),
            ) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_artifact(r) for r in rows]

    async def list_artifacts_for_tasks(self, shadow_task_ids: list[str]) -> list[CorporateArtifact]:
        """List all corporate artifacts for a batch of task IDs (e.g. parent DAG tasks)."""
        if not shadow_task_ids:
            return []

        placeholders = ",".join(["?"] * len(shadow_task_ids))
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                f"SELECT * FROM corporate_artifacts WHERE shadow_task_id IN ({placeholders}) ORDER BY created_at ASC",
                shadow_task_ids,
            ) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_artifact(r) for r in rows]
