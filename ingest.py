import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from parser import save_parsed_file
from retrieve import (create_chunks,build_index)

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
WORKSPACES_DIR = DATA_DIR / "workspaces"
REGISTRY_FILE = DATA_DIR / "registry.json"

WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)


def load_registry():
    """Load the global file registry safely."""

    if not REGISTRY_FILE.exists():
        return {}

    try:
        with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()

            if not content:
                return {}

            return json.loads(content)

    except json.JSONDecodeError:
        return {}


def save_registry(registry):
    """Save the global file registry."""

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
        json.dump(
            registry,
            f,
            indent=4
        )


def calculate_sha256(file_bytes: bytes) -> str:
    """Calculate SHA-256 hash of file content."""

    return hashlib.sha256(file_bytes).hexdigest()


def create_workspace(name: str):
    """Create a new persistent workspace."""

    workspace_id = str(uuid4())

    workspace_dir = WORKSPACES_DIR / workspace_id

    (workspace_dir / "files").mkdir(parents=True)
    (workspace_dir / "parsed").mkdir(parents=True)
    (workspace_dir / "index").mkdir(parents=True)
    (workspace_dir / "outputs").mkdir(parents=True)

    metadata = {
        "workspace_id": workspace_id,
        "name": name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "files": []
    }

    with open(
        workspace_dir / "workspace.json",
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            metadata,
            f,
            indent=4
        )

    return metadata


def get_workspace(workspace_id: str):
    """Return workspace metadata."""

    workspace_file = (
        WORKSPACES_DIR
        / workspace_id
        / "workspace.json"
    )

    if not workspace_file.exists():
        return None

    with open(
        workspace_file,
        "r",
        encoding="utf-8"
    ) as f:
        return json.load(f)


def update_workspace(workspace_id: str, file_metadata: dict):
    """Add uploaded file information to workspace metadata."""

    workspace_file = (
        WORKSPACES_DIR
        / workspace_id
        / "workspace.json"
    )

    if not workspace_file.exists():
        raise ValueError("Workspace does not exist.")

    with open(
        workspace_file,
        "r",
        encoding="utf-8"
    ) as f:
        workspace = json.load(f)

    workspace["files"].append(file_metadata)

    with open(
        workspace_file,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            workspace,
            f,
            indent=4
        )


def save_file(
    workspace_id: str,
    filename: str,
    file_bytes: bytes
):
    """
    Store and process a file.

    Workflow:
        1. Calculate SHA-256
        2. Check duplicate
        3. Save original file
        4. Parse document
        5. Save parsed JSON
        6. Update metadata
    """

    workspace_dir = WORKSPACES_DIR / workspace_id

    if not workspace_dir.exists():
        raise ValueError("Workspace does not exist.")

    file_hash = calculate_sha256(file_bytes)

    registry = load_registry()

    # ---------------------------------------------------------
    # 1. DUPLICATE CHECK
    # ---------------------------------------------------------

    if file_hash in registry:

        existing = registry[file_hash]

        return {
            "status": "duplicate",
            "message": "File already processed. Skipping ingestion.",
            "sha256": file_hash,
            "existing_file": existing
        }

    # ---------------------------------------------------------
    # 2. FILE INFORMATION
    # ---------------------------------------------------------

    file_id = str(uuid4())

    file_extension = Path(filename).suffix.lower()

    file_path = (
        workspace_dir
        / "files"
        / filename
    )

    # ---------------------------------------------------------
    # 3. SAVE ORIGINAL FILE
    # ---------------------------------------------------------

    with open(file_path, "wb") as f:
        f.write(file_bytes)

    # Parsed output location
    parsed_path = (
        workspace_dir
        / "parsed"
        / f"{file_id}.json"
    )

    # ---------------------------------------------------------
    # 4. PARSE DOCUMENT
    # ---------------------------------------------------------

    try:

        parsed_data = save_parsed_file(
            file_path=str(file_path),
            output_path=str(parsed_path)
        )

        chunks = create_chunks(parsed_data)

        index_path = (
            workspace_dir
            / "index"
            / f"{file_id}.faiss"
        )

        metadata_path = (
            workspace_dir
            / "index"
            / f"{file_id}_chunks.json"
        )

        build_index(
            chunks=chunks,
            index_path=str(index_path),
            metadata_path=str(metadata_path)
        )

        processed = True
        processing_error = None

    except Exception as e:

        processed = False
        processing_error = str(e)

    # ---------------------------------------------------------
    # 5. FILE METADATA
    # ---------------------------------------------------------

    file_metadata = {
        "file_id": file_id,
        "filename": filename,
        "sha256": file_hash,
        "file_type": file_extension,
        "size_bytes": len(file_bytes),
        "processed": processed,
        "parsed_file": str(parsed_path) if processed else None,
        "processing_error": processing_error,
        "uploaded_at": datetime.now(timezone.utc).isoformat()
    }

    # ---------------------------------------------------------
    # 6. UPDATE REGISTRY
    # ---------------------------------------------------------

    registry[file_hash] = {
        "workspace_id": workspace_id,
        "file_id": file_id,
        "filename": filename,
        "file_type": file_extension,
        "processed": processed
    }

    save_registry(registry)

    # ---------------------------------------------------------
    # 7. UPDATE WORKSPACE
    # ---------------------------------------------------------

    update_workspace(
        workspace_id,
        file_metadata
    )

    # ---------------------------------------------------------
    # 8. RESPONSE
    # ---------------------------------------------------------

    if processed:

        return {
            "status": "uploaded",
            "message": "File uploaded and processed successfully.",
            "file": file_metadata
        }

    return {
        "status": "uploaded",
        "message": "File uploaded but processing failed.",
        "file": file_metadata
    }