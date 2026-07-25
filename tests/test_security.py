"""Unit tests for JWT security, password hashing, and file upload sanitization."""

from __future__ import annotations

import io
from pathlib import Path
import pytest
from shadow_adapter.config import ShadowConfig
from shadow_adapter.security import SecurityManager
from shadow_adapter.upload import SecureUploadHandler, UploadValidationError


def test_password_hashing() -> None:
    """Test bcrypt password hashing and verification."""
    plain = "SuperSecretPass123!"
    hashed = SecurityManager.hash_password(plain)

    assert hashed != plain
    assert SecurityManager.verify_password(plain, hashed) is True
    assert SecurityManager.verify_password("WrongPassword", hashed) is False


def test_jwt_token_round_trip(shadow_config: ShadowConfig) -> None:
    """Test JWT creation and decoding."""
    security = SecurityManager(shadow_config)

    token = security.create_access_token(
        contractor_id="c_12345",
        username="jane_contractor",
        roles=["contractor", "admin"],
        custom_claims={"tenant": "acme"},
    )

    payload = security.decode_token(token)
    assert payload["sub"] == "c_12345"
    assert payload["username"] == "jane_contractor"
    assert "admin" in payload["roles"]
    assert payload["tenant"] == "acme"


def test_jwt_invalid_secret(shadow_config: ShadowConfig) -> None:
    """Test that decoding a token signed with a different secret fails."""
    sec1 = SecurityManager(shadow_config)

    config_bad = ShadowConfig(jwt_secret="completely-different-secret-key-000")
    sec2 = SecurityManager(config_bad)

    token = sec1.create_access_token("c_123", "user", ["contractor"])

    with pytest.raises(ValueError, match="Invalid or expired token"):
        sec2.decode_token(token)


def test_filename_sanitization(shadow_config: ShadowConfig) -> None:
    """Test path traversal prevention during filename sanitization."""
    handler = SecureUploadHandler(shadow_config)

    # Path traversal attack vectors
    assert handler.sanitize_filename("../../etc/passwd") == "passwd"
    assert handler.sanitize_filename("..\\..\\windows\\system32\\cmd.exe") == "cmd.exe"
    assert handler.sanitize_filename("my report (v1!).pdf") == "my_report__v1__.pdf"
    assert handler.sanitize_filename(".hidden_file.txt") == "hidden_file.txt"


def test_extension_validation(shadow_config: ShadowConfig) -> None:
    """Test extension allowlist validation."""
    handler = SecureUploadHandler(shadow_config)

    assert handler.validate_extension("report.pdf") == ".pdf"
    assert handler.validate_extension("data.docx") == ".docx"
    assert handler.validate_extension("archive.tar.gz") == ".tar.gz"

    with pytest.raises(UploadValidationError, match="not allowed"):
        handler.validate_extension("malicious_script.exe")

    with pytest.raises(UploadValidationError, match="not allowed"):
        handler.validate_extension("shell_script.sh")
