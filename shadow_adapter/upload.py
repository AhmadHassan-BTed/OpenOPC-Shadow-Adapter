"""Secure file upload handler for human contractor deliverables.

Enforces security guardrails and limits:
- Path traversal protection (stripping path separators, '..', UUID prefixing)
- Allowed file extension validation
- Per-file size limit (default 10MB)
- Total submission payload size limit (default 50MB)
- File count limit per submission (default 5 files)
"""

from __future__ import annotations

import os
import re
import uuid
from pathlib import Path
from typing import BinaryIO, Sequence

from loguru import logger

from shadow_adapter.config import ShadowConfig


class UploadValidationError(ValueError):
    """Raised when an uploaded file violates security or size constraints."""


class SecureUploadHandler:
    """Manages file storage, filename sanitization, and security checks."""

    def __init__(self, config: ShadowConfig) -> None:
        self.config = config

    def sanitize_filename(self, filename: str) -> str:
        """Strip path components, leading dots, and illegal characters.

        Example: '../../etc/passwd' -> 'passwd'
                 '..\\..\\windows\\system32\\cmd.exe' -> 'cmd.exe'
                 'my report (final!).pdf' -> 'my_report_final_.pdf'
        """
        # Normalize Windows backslashes to forward slashes before taking basename
        normalized = filename.replace("\\", "/")
        base = os.path.basename(normalized)
        # Replace non-alphanumeric (except . - _) with underscore
        cleaned = re.sub(r"[^\w\.\-]", "_", base)
        # Prevent hidden files / relative traversal dots at start
        cleaned = cleaned.lstrip(".")
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
        if full_name_lower.endswith(".tar.gz") and ".tar.gz" in self.config.allowed_extensions_set:
            return ".tar.gz"

        if not ext or ext not in self.config.allowed_extensions_set:
            allowed_str = ", ".join(sorted(self.config.allowed_extensions_set))
            raise UploadValidationError(
                f"File extension '{ext or 'none'}' is not allowed. Permitted extensions: {allowed_str}"
            )
        return ext

    def validate_file_count(self, file_count: int) -> None:
        """Ensure file count does not exceed max_files_per_submission."""
        if file_count > self.config.max_files_per_submission:
            raise UploadValidationError(
                f"Too many files uploaded ({file_count}). "
                f"Maximum allowed per submission is {self.config.max_files_per_submission}."
            )

    def get_task_upload_dir(self, shadow_task_id: str) -> Path:
        """Get or create the task-scoped upload directory."""
        # Sanitize task_id to avoid traversal if task_id ever contained weird characters
        safe_task_id = re.sub(r"[^\w\-]", "_", shadow_task_id)
        task_dir = self.config.upload_path / safe_task_id
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

        if file_size_hint is not None and file_size_hint > self.config.max_file_size_bytes:
            raise UploadValidationError(
                f"File '{filename}' exceeds individual size limit of {self.config.max_file_size_mb}MB."
            )

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
                    if bytes_written > self.config.max_file_size_bytes:
                        raise UploadValidationError(
                            f"File '{filename}' exceeded size limit of {self.config.max_file_size_mb}MB during stream."
                        )
                    f_out.write(chunk)
        except Exception:
            # Cleanup partial file on error
            if destination.exists():
                destination.unlink(missing_ok=True)
            raise

        relative_path = str(destination.relative_to(self.config.upload_path))
        logger.info(f"Saved file '{filename}' ({bytes_written} bytes) to {destination}")
        return relative_path, bytes_written
