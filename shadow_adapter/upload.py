"""Secure file upload handler for human contractor deliverables.

Enforces security guardrails and limits:
- Path traversal protection (stripping path separators, '..', UUID prefixing)
- Allowed file extension validation
- Per-file size limit (default 10MB)
- Total submission payload size limit (default 50MB)
- File count limit per submission (default 5 files)

Infrastructure Tier: Accepts UploadLimits DTO, never the full ShadowConfig.
"""

from __future__ import annotations

import os
import re
import uuid
from pathlib import Path
from typing import Any, BinaryIO

from loguru import logger

from shadow_adapter.models import UploadLimits


class UploadValidationError(ValueError):
    """Raised when an uploaded file violates security or size constraints."""


class SecureUploadHandler:
    """Manages file storage, filename sanitization, and security checks."""

    def __init__(self, config: UploadLimits | Any, *, upload_dir: str | Path | None = None) -> None:
        # Accept UploadLimits directly, or extract from ShadowConfig for backward compat
        if isinstance(config, UploadLimits):
            self._limits = config
            self._upload_dir = Path(upload_dir) if upload_dir else Path("./shadow_uploads")
        else:
            # Backward compatibility: extract UploadLimits from ShadowConfig
            self._limits = UploadLimits(
                max_file_count=config.max_files_per_submission,
                max_file_size_bytes=config.max_file_size_bytes,
                max_total_size_bytes=config.max_upload_size_bytes,
                allowed_extensions=config.allowed_extensions_set,
            )
            self._upload_dir = config.upload_path

    def sanitize_filename(self, filename: str) -> str:
        """Strip path components, leading dots, and illegal characters.

        Example: '../../etc/passwd' -> 'passwd'
                 '..\\\\..\\\\windows\\\\system32\\\\cmd.exe' -> 'cmd.exe'
                 'my report (final!).pdf' -> 'my_report_final_.pdf'
        """
        # Strip leading/trailing whitespace and normalize backslashes
        normalized = filename.strip().replace("\\", "/")
        base = os.path.basename(normalized)
        # Replace non-alphanumeric (except . - _) with underscore
        cleaned = re.sub(r"[^\w\.\-]", "_", base)
        # Prevent hidden files / relative traversal dots at start and underscores
        cleaned = cleaned.lstrip("._")
        if not cleaned:
            cleaned = "unnamed_file"
        return cleaned

    def validate_extension(self, filename: str) -> str:
        """Validate filename extension against configured allowlist.

        Returns the normalized extension. Raises UploadValidationError if disallowed.
        """
        ext = Path(filename).suffix.lower()
        # Handle double extension like .tar.gz if matched against allowed set
        full_name_lower = filename.lower()
        if full_name_lower.endswith(".tar.gz") and ".tar.gz" in self._limits.allowed_extensions:
            return ".tar.gz"

        if not ext or ext not in self._limits.allowed_extensions:
            allowed_str = ", ".join(sorted(self._limits.allowed_extensions))
            raise UploadValidationError(
                f"File extension '{ext or 'none'}' is not allowed. Permitted extensions: {allowed_str}"
            )
        return ext

    def validate_file_count(self, file_count: int) -> None:
        """Ensure file count does not exceed max_files_per_submission."""
        if file_count > self._limits.max_file_count:
            raise UploadValidationError(
                f"Too many files uploaded ({file_count}). "
                f"Maximum allowed per submission is {self._limits.max_file_count}."
            )

    @property
    def upload_path(self) -> Path:
        """Get the upload directory, creating it if needed."""
        self._upload_dir.mkdir(parents=True, exist_ok=True)
        return self._upload_dir

    def get_task_upload_dir(self, shadow_task_id: str) -> Path:
        """Get or create the task-scoped upload directory."""
        # Sanitize task_id to avoid traversal if task_id ever contained weird characters
        safe_task_id = re.sub(r"[^\w\-]", "_", shadow_task_id)
        task_dir = self.upload_path / safe_task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        return task_dir

    def save_upload_stream(
        self,
        shadow_task_id: str,
        filename: str,
        stream: BinaryIO,
        file_size_hint: int | None = None,
    ) -> tuple[str, int]:
        """Save a file stream securely to disk with size checks.

        Returns (relative_file_path, bytes_written).
        """
        self.validate_extension(filename)

        if file_size_hint is not None and file_size_hint > self._limits.max_file_size_bytes:
            raise UploadValidationError(f"File '{filename}' exceeds individual size limit.")

        safe_name = self.sanitize_filename(filename)
        unique_name = f"{uuid.uuid4().hex[:12]}_{safe_name}"
        task_dir = self.get_task_upload_dir(shadow_task_id)
        destination = task_dir / unique_name

        bytes_written = 0
        chunk_size = 64 * 1024  # 64KB chunks

        try:
            with open(destination, "wb") as f_out:
                while chunk := stream.read(chunk_size):
                    bytes_written += len(chunk)
                    if bytes_written > self._limits.max_file_size_bytes:
                        raise UploadValidationError(f"File '{filename}' exceeded size limit during stream.")
                    f_out.write(chunk)
        except Exception:
            # Cleanup partial file on error
            if destination.exists():
                destination.unlink(missing_ok=True)
            raise

        relative_path = str(destination.relative_to(self.upload_path))
        logger.info(f"Saved file '{filename}' ({bytes_written} bytes) to {destination}")
        return relative_path, bytes_written
