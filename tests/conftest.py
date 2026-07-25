"""Pytest configuration and shared fixtures for openopc-shadow-adapter test suite."""

from __future__ import annotations

import asyncio
import sqlite3
import uuid
from pathlib import Path
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from shadow_adapter.api.app import create_app
from shadow_adapter.config import ShadowConfig
from shadow_adapter.models import ShadowContractor
from shadow_adapter.security import SecurityManager
from shadow_adapter.shadow_store import ShadowStore
from shadow_adapter.upload import SecureUploadHandler

pytestmark = pytest.mark.asyncio


@pytest.fixture
def shadow_config(tmp_path: Path) -> ShadowConfig:
    """Provide a ShadowConfig instance pointing to temporary test directories."""
    return ShadowConfig(
        db_path=str(tmp_path / "shadow_tasks.db"),
        upload_dir=str(tmp_path / "shadow_uploads"),
        opc_store_path=str(tmp_path / "opc_store.db"),
        jwt_secret="test-jwt-secret-key-9999",
        jwt_expire_hours=1,
        max_files_per_submission=5,
        max_file_size_mb=10,
        max_total_upload_size_mb=50,
    )


@pytest_asyncio.fixture
async def shadow_store(shadow_config: ShadowConfig) -> AsyncGenerator[ShadowStore, None]:
    """Provide an initialized ShadowStore instance using an isolated temp SQLite DB."""
    store = ShadowStore(shadow_config.db_path)
    await store.initialize()
    yield store
    await store.close()


@pytest.fixture
def security(shadow_config: ShadowConfig) -> SecurityManager:
    """Provide a SecurityManager instance."""
    return SecurityManager(shadow_config)


@pytest.fixture
def mock_opc_store_path(shadow_config: ShadowConfig) -> Path:
    """Create a mock OpenOPC store.db with tasks and delegation_work_items tables."""
    db_path = Path(shadow_config.opc_store_path)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            session_id TEXT,
            title TEXT,
            description TEXT,
            assigned_to TEXT,
            status TEXT DEFAULT 'pending',
            priority INTEGER DEFAULT 5,
            project_id TEXT DEFAULT 'default',
            metadata TEXT DEFAULT '{}',
            result TEXT,
            execution_lock INTEGER DEFAULT 0,
            execution_locked_at TEXT,
            created_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS delegation_work_items (
            work_item_id TEXT PRIMARY KEY,
            run_id TEXT,
            role_id TEXT,
            title TEXT,
            phase TEXT DEFAULT 'ready',
            metadata TEXT DEFAULT '{}',
            created_at TEXT,
            updated_at TEXT
        )
    """)
    conn.commit()
    conn.close()
    return db_path


@pytest_asyncio.fixture
async def test_contractor(shadow_store: ShadowStore, security: SecurityManager) -> ShadowContractor:
    """Create a default test contractor account."""
    pwd_hash = security.hash_password("testpassword123")
    contractor = ShadowContractor(
        username=f"contractor_{uuid.uuid4().hex[:6]}",
        email="test@example.com",
        password_hash=pwd_hash,
        display_name="Test Contractor",
        roles=["contractor"],
    )
    return await shadow_store.create_contractor(contractor)


@pytest_asyncio.fixture
async def test_admin(shadow_store: ShadowStore, security: SecurityManager) -> ShadowContractor:
    """Create an admin contractor account."""
    pwd_hash = security.hash_password("adminpassword123")
    admin = ShadowContractor(
        username=f"admin_{uuid.uuid4().hex[:6]}",
        email="admin@example.com",
        password_hash=pwd_hash,
        display_name="Test Admin",
        roles=["admin", "contractor"],
    )
    return await shadow_store.create_contractor(admin)


@pytest.fixture
def auth_headers(test_contractor: ShadowContractor, security: SecurityManager) -> dict[str, str]:
    """Provide HTTP Bearer authorization headers for test_contractor."""
    token = security.create_access_token(
        contractor_id=test_contractor.id,
        username=test_contractor.username,
        roles=test_contractor.roles,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers(test_admin: ShadowContractor, security: SecurityManager) -> dict[str, str]:
    """Provide HTTP Bearer authorization headers for test_admin."""
    token = security.create_access_token(
        contractor_id=test_admin.id,
        username=test_admin.username,
        roles=test_admin.roles,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def client(shadow_config: ShadowConfig, mock_opc_store_path: Path) -> AsyncGenerator[AsyncClient, None]:
    """Provide an AsyncClient with initialized app lifespan state."""
    app = create_app(shadow_config)

    # Initialize state explicitly for TestClient ASGI transport
    store = ShadowStore(shadow_config.db_path)
    await store.initialize()
    app.state.config = shadow_config
    app.state.shadow_store = store
    app.state.security = SecurityManager(shadow_config)
    app.state.upload_handler = SecureUploadHandler(shadow_config)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        yield ac

    await store.close()
