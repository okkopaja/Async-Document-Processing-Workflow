from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Protocol
from uuid import uuid4


class StorageValidationError(Exception):
	def __init__(self, code: str, message: str, status_code: int) -> None:
		super().__init__(message)
		self.code = code
		self.message = message
		self.status_code = status_code


@dataclass(slots=True)
class StoredFile:
	original_filename: str
	stored_filename: str
	mime_type: str
	extension: str
	size_bytes: int
	storage_path: str


class StorageService(Protocol):
	def save_upload(
		self,
		file_bytes: bytes,
		document_id: str,
		original_name: str,
		content_type: str | None = None,
	) -> StoredFile: ...

	def open_for_read(self, storage_path: str) -> BinaryIO: ...

	def exists(self, storage_path: str) -> bool: ...

	def delete_document_artifacts(
		self,
		document_id: str,
		storage_path: str | None = None,
	) -> None: ...


class LocalStorageService:
	_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")

	def __init__(self, upload_dir: str, max_upload_mb: int, allowed_extensions: list[str]) -> None:
		self.upload_root = Path(upload_dir).resolve()
		self.max_upload_bytes = max_upload_mb * 1024 * 1024
		self.allowed_extensions = {ext.lower().lstrip(".") for ext in allowed_extensions}
		self.upload_root.mkdir(parents=True, exist_ok=True)

	def save_upload(
		self,
		file_bytes: bytes,
		document_id: str,
		original_name: str,
		content_type: str | None = None,
	) -> StoredFile:
		if len(file_bytes) == 0:
			raise StorageValidationError(
				code="VALIDATION_ERROR",
				message="Uploaded file is empty.",
				status_code=422,
			)

		if len(file_bytes) > self.max_upload_bytes:
			raise StorageValidationError(
				code="FILE_TOO_LARGE",
				message="Uploaded file exceeds the configured size limit.",
				status_code=413,
			)

		extension = self._extract_extension(original_name)
		if extension not in self.allowed_extensions:
			raise StorageValidationError(
				code="UNSUPPORTED_FILE_TYPE",
				message=f"Extension '{extension}' is not allowed.",
				status_code=400,
			)

		safe_original = self._sanitize_filename(original_name)
		stored_filename = f"{uuid4().hex}_{safe_original}"
		target_dir = (self.upload_root / document_id).resolve()
		target_dir.mkdir(parents=True, exist_ok=True)
		target_path = (target_dir / stored_filename).resolve()

		self._ensure_within_upload_root(target_path)

		with target_path.open("wb") as buffer:
			buffer.write(file_bytes)

		return StoredFile(
			original_filename=original_name,
			stored_filename=stored_filename,
			mime_type=content_type or "application/octet-stream",
			extension=extension,
			size_bytes=len(file_bytes),
			storage_path=str(target_path),
		)

	def open_for_read(self, storage_path: str) -> BinaryIO:
		target_path = Path(storage_path).resolve()
		self._ensure_within_upload_root(target_path)
		return target_path.open("rb")

	def exists(self, storage_path: str) -> bool:
		target_path = Path(storage_path).resolve()
		self._ensure_within_upload_root(target_path)
		return target_path.exists()

	def delete_document_artifacts(
		self,
		document_id: str,
		storage_path: str | None = None,
	) -> None:
		if storage_path:
			target_path = Path(storage_path).resolve()
			self._ensure_within_upload_root(target_path)
			if target_path.exists() and target_path.is_file():
				target_path.unlink()

		document_dir = (self.upload_root / document_id).resolve()
		self._ensure_within_upload_root(document_dir)
		if document_dir.exists() and document_dir.is_dir():
			shutil.rmtree(document_dir)

	def _sanitize_filename(self, filename: str) -> str:
		basename = os.path.basename(filename).strip()
		if not basename:
			basename = "upload.txt"
		sanitized = self._FILENAME_RE.sub("_", basename)
		sanitized = sanitized.strip("._")
		return sanitized or "upload.txt"

	def _extract_extension(self, filename: str) -> str:
		suffix = Path(filename).suffix.lower().lstrip(".")
		return suffix

	def _ensure_within_upload_root(self, candidate: Path) -> None:
		try:
			candidate.resolve().relative_to(self.upload_root)
		except ValueError:
			raise StorageValidationError(
				code="VALIDATION_ERROR",
				message="Invalid storage path.",
				status_code=422,
			)
