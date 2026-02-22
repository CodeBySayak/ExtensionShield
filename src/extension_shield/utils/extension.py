"""
Chrome Extension Utilities

This module provides utilities for extracting, analyzing, and managing Chrome extensions.
"""

import zipfile
import tempfile
import os
import re
import logging
import hashlib
import struct
from typing import Optional

from extension_shield.core.config import get_settings

logger = logging.getLogger(__name__)

# CRX magic bytes (all CRX versions)
CRX_MAGIC = b"Cr24"

# Single source of truth: Chrome extension IDs are exactly 32 lowercase letters [a-z]
CHROME_EXTENSION_ID_PATTERN = re.compile(r"^[a-z]{32}$")


def _check_zip_bomb_limits(zip_ref: zipfile.ZipFile, max_files: int, max_uncompressed_bytes: int) -> None:
    """
    Reject archive before extraction if it exceeds zip-bomb limits.
    Raises ValueError if file count or total uncompressed size is over limit.
    """
    file_count = 0
    total_uncompressed = 0
    for member in zip_ref.infolist():
        if member.is_dir():
            continue
        file_count += 1
        if file_count > max_files:
            raise ValueError(
                f"Zip file count ({file_count}) exceeds limit ({max_files}). "
                "Refusing to extract (zip-bomb protection)."
            )
        # file_size is uncompressed size; may be -1 for unknown in some zips
        size = getattr(member, "file_size", 0) or 0
        if size < 0:
            size = 0
        total_uncompressed += size
        if total_uncompressed > max_uncompressed_bytes:
            raise ValueError(
                f"Zip total uncompressed size ({total_uncompressed}) exceeds limit ({max_uncompressed_bytes}). "
                "Refusing to extract (zip-bomb protection)."
            )


def extract_extension_id_by_url(url):
    """Extract extension ID from Chrome Web Store URL. Returns only if it matches ^[a-z]{32}$."""
    try:
        if not url or not isinstance(url, str):
            return None
        candidate = None
        # Handle different URL formats
        if "/detail/" in url:
            parts = url.split("/detail/")
            if len(parts) > 1:
                extension_part = parts[1]
                candidate = extension_part.split("/")[-1].split("?")[0].rstrip("/").strip().lower()
        elif "id=" in url:
            match = re.search(r"id=([^&]+)", url)
            if match:
                candidate = match.group(1).strip().lower()

        if candidate and CHROME_EXTENSION_ID_PATTERN.match(candidate):
            return candidate
        if candidate:
            logger.warning("Extracted ID from URL did not match Chrome ID format [a-z]{32}: %s", candidate[:50])
        else:
            logger.warning("Could not extract extension ID from URL")
        return None

    except Exception as exc:
        logger.error("Error extracting extension ID: %s", exc)
        return None


def calculate_file_hash(file_path: str) -> Optional[str]:
    """Calculate SHA256 hash of downloaded file"""
    try:
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    except Exception as exc:
        logger.error("Error calculating file hash: %s", exc)
        return None


def _crx_zip_offset(file_path: str) -> Optional[int]:
    """
    Return the byte offset at which the ZIP payload starts in a CRX file.
    CRX v2: magic(4) + version(4) + pk_len(4) + sig_len(4) + pk + sig → ZIP.
    CRX v3: magic(4) + version(4) + header_len(4) + header → ZIP.
    Returns None if the file is not a valid CRX or format is unsupported.
    """
    try:
        with open(file_path, "rb") as f:
            magic = f.read(4)
            if magic != CRX_MAGIC:
                return None
            version_bytes = f.read(4)
            if len(version_bytes) < 4:
                return None
            version = struct.unpack("<I", version_bytes)[0]
            if version == 2:
                # pk_len (4) + sig_len (4) + pk + sig
                pk_len = struct.unpack("<I", f.read(4))[0]
                sig_len = struct.unpack("<I", f.read(4))[0]
                # Skip public key and signature
                f.seek(pk_len + sig_len, 1)
                return f.tell()
            if version == 3:
                header_len = struct.unpack("<I", f.read(4))[0]
                f.seek(header_len, 1)
                return f.tell()
            logger.warning("Unsupported CRX version: %s", version)
            return None
    except (OSError, struct.error) as e:
        logger.warning("Failed to read CRX header: %s", e)
        return None


def _has_manifest(files: list) -> bool:
    """True if any file in list is manifest.json (case-insensitive)."""
    return any(f.lower() == "manifest.json" for f in files)


def resolve_extension_root(extract_dir: str) -> Optional[str]:
    """
    Return the directory that contains manifest.json, handling zips that have
    a single top-level folder (e.g. when zipping from Chrome's Extensions folder).

    Search is under extension_storage: extract_dir is always
    <EXTENSION_STORAGE_PATH>/extracted_<basename>_<pid>.

    - If manifest.json is in extract_dir, returns extract_dir.
    - If manifest.json (any case) is in one or more subdirs, returns the shallowest one.
    - If no manifest.json is found, returns None (caller should not use extract_dir as root).
    """
    if not extract_dir or not os.path.isdir(extract_dir):
        return None
    root_manifest = os.path.join(extract_dir, "manifest.json")
    if os.path.isfile(root_manifest):
        return extract_dir
    # Case-insensitive: e.g. Manifest.json
    for name in os.listdir(extract_dir):
        if name.lower() == "manifest.json":
            return extract_dir
    candidates = []
    extract_dir_abs = os.path.abspath(extract_dir)
    for root, _dirs, files in os.walk(extract_dir):
        if _has_manifest(files):
            candidates.append(os.path.abspath(root))
    if not candidates:
        try:
            top_level = os.listdir(extract_dir)
            logger.warning(
                "No manifest.json found under %s (extension_storage). Top-level contents: %s",
                extract_dir,
                top_level[:20],
            )
        except OSError:
            pass
        return None
    # Prefer the shallowest path (closest to extract_dir) so we get the real extension root
    def depth_from_extract(p: str) -> int:
        try:
            rel = os.path.relpath(p, extract_dir_abs)
            if rel == ".":
                return 0
            return len(rel.split(os.sep))
        except ValueError:
            return 999
    candidates.sort(key=lambda p: (depth_from_extract(p), p))
    chosen = candidates[0]
    if len(candidates) > 1:
        logger.info(
            "Resolved extension root to shallowest subdirectory with manifest.json: %s",
            os.path.basename(chosen),
        )
    else:
        logger.info(
            "Resolved extension root to subdirectory (zip had top-level folder): %s",
            os.path.basename(chosen),
        )
    return chosen


def extract_extension_crx(file_path: str) -> Optional[str]:
    """Extract .crx or .zip file to a persistent directory for file viewing.

    Extraction always happens under the configured EXTENSION_STORAGE_PATH, resolved
    to an absolute path so the extract dir is exact (e.g. /app/extensions_storage/extracted_...).
    """
    try:
        # Resolve to absolute path so extraction uses exact configured location (local or /app/...)
        storage_path = get_settings().extension_storage_path
        storage_path_abs = os.path.abspath(os.path.normpath(storage_path))
        os.makedirs(storage_path_abs, exist_ok=True)

        base_name = os.path.basename(file_path)
        extract_dir_name = f"extracted_{base_name}_{os.getpid()}"
        extract_dir = os.path.join(storage_path_abs, extract_dir_name)
        os.makedirs(extract_dir, exist_ok=True)

        logger.info("Extracting to extension_storage (exact path): %s", extract_dir)

        if file_path.lower().endswith(".crx"):
            # CRX files have a header (v2 or v3) before the ZIP payload
            zip_offset = _crx_zip_offset(file_path)
            if zip_offset is None:
                logger.error("Invalid or unsupported CRX format: %s", file_path)
                return None
            with open(file_path, "rb") as f:
                f.seek(zip_offset)
                zip_data = f.read()

            temp_zip = os.path.join(extract_dir, "temp.zip")
            with open(temp_zip, "wb") as f:
                f.write(zip_data)

            with zipfile.ZipFile(temp_zip, "r") as zip_ref:
                settings = get_settings()
                _check_zip_bomb_limits(
                    zip_ref,
                    settings.zip_extract_max_files,
                    settings.zip_extract_max_uncompressed_bytes,
                )
                # Safe extraction with zip-slip protection
                for member in zip_ref.infolist():
                    # Normalize path and check for zip-slip
                    target_path = os.path.join(extract_dir, member.filename)
                    abs_target = os.path.abspath(target_path)
                    abs_extract = os.path.abspath(extract_dir)
                    if not abs_target.startswith(abs_extract):
                        raise ValueError(f"Zip-slip attempt detected: {member.filename}")
                    zip_ref.extract(member, extract_dir)

            os.remove(temp_zip)

        elif file_path.lower().endswith(".zip"):
            # Direct ZIP extraction with zip-slip protection
            with zipfile.ZipFile(file_path, "r") as zip_ref:
                settings = get_settings()
                _check_zip_bomb_limits(
                    zip_ref,
                    settings.zip_extract_max_files,
                    settings.zip_extract_max_uncompressed_bytes,
                )
                # Safe extraction with zip-slip protection
                for member in zip_ref.infolist():
                    # Normalize path and check for zip-slip
                    target_path = os.path.join(extract_dir, member.filename)
                    abs_target = os.path.abspath(target_path)
                    abs_extract = os.path.abspath(extract_dir)
                    if not abs_target.startswith(abs_extract):
                        raise ValueError(f"Zip-slip attempt detected: {member.filename}")
                    zip_ref.extract(member, extract_dir)

        else:
            logger.error("Unsupported file format for extraction: %s", file_path)
            return None

        # If the zip had a single top-level folder (e.g. Chrome's version folder),
        # manifest.json lives inside it; resolve to that directory so the rest of
        # the pipeline finds manifest.json at the extension root.
        return resolve_extension_root(extract_dir) or extract_dir
    except ValueError:
        # Zip-bomb and zip-slip rejections: propagate to caller
        raise
    except Exception as exc:
        logger.error("Error extracting .crx file: %s", exc)
        return None


def cleanup_downloaded_crx(crx_file_path: str):
    """
    Remove a downloaded CRX file with safety checks.

    Only deletes files within the extensions_storage directory.
    Logs warning if file doesn't exist (idempotent).

    Args:
        crx_file_path (str): Path to the CRX file to remove.

    Raises:
        ValueError: If file path is outside extensions_storage directory.
        OSError: If file deletion fails.
    """
    try:
        if not os.path.exists(crx_file_path):
            logger.warning("CRX file does not exist (already cleaned?): %s", crx_file_path)
            return

        # Safety: Only delete files within storage directory
        abs_crx_path = os.path.abspath(crx_file_path)
        storage_path = get_settings().extension_storage_path
        abs_storage_path = os.path.abspath(storage_path)

        if not abs_crx_path.startswith(abs_storage_path):
            logger.warning(
                "Refusing to delete CRX file outside storage directory: %s",
                abs_crx_path,
            )
            raise ValueError(f"CRX file path outside storage directory: {abs_crx_path}")

        os.remove(crx_file_path)
        logger.info("Cleaned up CRX file: %s", crx_file_path)

    except Exception as exc:
        logger.error("Error cleaning up CRX file %s: %s", crx_file_path, exc)
        raise


def is_chrome_extension_store_url(path: str) -> bool:
    """
    Check if the provided path is a valid Chrome Web Store URL

    Example:
        - "https://chromewebstore.google.com/detail/
          fantasypros-win-your-fant/gfbepnlhpkbgbkcebjnfhgjckibfdfkc"

    Args:
        path (str): The URL to check.

    Returns:
        bool: True if the URL matches the Chrome Web Store pattern, False otherwise.
    """
    return path.startswith("https://chromewebstore.google.com/detail/")


def is_local_extension_crx_file(path: str) -> bool:
    """
    Check if the provided path is a local CRX or ZIP file

    Args:
        path (str): The file path to check.

    Returns:
        bool: True if the path is a local .crx or .zip file, False otherwise.
    """
    if not path:
        return False
    return os.path.isfile(path) and (path.lower().endswith(".crx") or path.lower().endswith(".zip"))


def is_chrome_extension_id(path: str) -> bool:
    """
    Check if the provided string is a valid Chrome extension ID.
    Must match ^[a-z]{32}$ (32 lowercase letters).
    """
    if not path or not isinstance(path, str):
        return False
    return bool(CHROME_EXTENSION_ID_PATTERN.match(path.strip().lower()))
