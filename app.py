from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.openapi.utils import get_openapi
from typing import List
from pydantic import BaseModel
from pathlib import Path

from ingest import (create_workspace,get_workspace,save_file,WORKSPACES_DIR)

from retrieve import search
from llm import generate_answer
from file_editor import (update_excel_cell,replace_word_text)

app = FastAPI(
    title="Treelife AI Workspace",
    description="Persistent multi-document AI workspace",
    version="1.0.0"
)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    upload_schema = schema["components"]["schemas"].get(
        "Body_upload_files_workspace__workspace_id__upload_post"
    )

    if upload_schema:
        files_schema = upload_schema["properties"].get("files")

        if files_schema:
            files_schema["items"]["format"] = "binary"
            files_schema["items"].pop("contentMediaType", None)

    app.openapi_schema = schema

    return app.openapi_schema


app.openapi = custom_openapi
class QueryRequest(BaseModel):
    question: str
    top_k: int = 5

class EditRequest(BaseModel):
    operation: str

    sheet: str | None = None
    cell: str | None = None
    value: object | None = None

    old_text: str | None = None
    new_text: str | None = None

@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.post("/workspace")
def create_new_workspace(name: str):
    """
    Create a new workspace.
    """

    workspace = create_workspace(name)

    return {
        "status": "success",
        "workspace": workspace
    }


@app.get("/workspace/{workspace_id}")
def get_workspace_details(workspace_id: str):
    """
    Get workspace information.
    """

    workspace = get_workspace(workspace_id)

    if workspace is None:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found."
        )

    return workspace


@app.post("/workspace/{workspace_id}/upload")
async def upload_files(
    workspace_id: str,
    files: List[UploadFile] = File(...)
):
    """
    Upload one or multiple files into a workspace.
    """

    workspace = get_workspace(workspace_id)

    if workspace is None:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found."
        )

    results = []

    for uploaded_file in files:

        file_bytes = await uploaded_file.read()

        result = save_file(
            workspace_id=workspace_id,
            filename=uploaded_file.filename,
            file_bytes=file_bytes
        )

        results.append(result)

    return {
        "workspace_id": workspace_id,
        "total_files": len(files),
        "results": results
    }

@app.post("/workspace/{workspace_id}/query")
def query_workspace(
    workspace_id: str,
    request: QueryRequest
):
    """
    Ask a question across all processed documents
    in the workspace.
    """

    workspace = get_workspace(workspace_id)

    if workspace is None:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found."
        )

    all_results = []

    workspace_dir = (
        WORKSPACES_DIR / workspace_id
    )

    # Search every processed document
    for file in workspace["files"]:

        if not file.get("processed"):
            continue

        file_id = file["file_id"]

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

        if not index_path.exists():
            continue

        results = search(
            query=request.question,
            index_path=str(index_path),
            metadata_path=str(metadata_path),
            top_k=request.top_k
        )

        all_results.extend(results)

    # Rank results from all documents together
    all_results.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    selected_results = all_results[:request.top_k]

    if not selected_results:
        return {
            "question": request.question,
            "answer": "No relevant information was found.",
            "sources": []
        }

    # Build LLM context
    context_parts = []

    for result in selected_results:

        source = f"Source: {result['filename']}"

        if result.get("page"):
            source += f", Page: {result['page']}"

        context_parts.append(
            f"{source}\n\n{result['text']}"
        )

    context = "\n\n---\n\n".join(context_parts)

    # Ask Gemma
    answer = generate_answer(
        question=request.question,
        context=context
    )

    sources = [
        {
            "filename": result["filename"],
            "page": result.get("page"),
            "score": round(result["score"], 4)
        }
        for result in selected_results
    ]

    return {
        "question": request.question,
        "answer": answer,
        "sources": sources
    }

@app.post("/workspace/{workspace_id}/edit/{file_id}")
def edit_file(
    workspace_id: str,
    file_id: str,
    request: EditRequest
):
    """
    Apply a deterministic edit to an uploaded document.
    """

    workspace = get_workspace(workspace_id)

    if workspace is None:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found."
        )

    target_file = None

    for file in workspace["files"]:
        if file["file_id"] == file_id:
            target_file = file
            break

    if target_file is None:
        raise HTTPException(
            status_code=404,
            detail="File not found."
        )

    workspace_dir = WORKSPACES_DIR / workspace_id

    input_path = (
        workspace_dir
        / "files"
        / target_file["filename"]
    )

    if not input_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Original file not found."
        )

    output_path = (
        workspace_dir
        / "outputs"
        / f"modified_{target_file['filename']}"
    )

    try:

        # Excel
        if target_file["file_type"] in [".xlsx", ".xlsm"]:

            if request.operation != "update_cell":
                raise ValueError(
                    "Excel currently supports only update_cell."
                )

            if not request.sheet:
                raise ValueError("sheet is required.")

            if not request.cell:
                raise ValueError("cell is required.")

            result = update_excel_cell(
                input_path=str(input_path),
                output_path=str(output_path),
                sheet=request.sheet,
                cell=request.cell,
                value=request.value
            )

        # Word
        elif target_file["file_type"] == ".docx":

            if request.operation != "replace_text":
                raise ValueError(
                    "DOCX currently supports only replace_text."
                )

            if request.old_text is None:
                raise ValueError("old_text is required.")

            if request.new_text is None:
                raise ValueError("new_text is required.")

            result = replace_word_text(
                input_path=str(input_path),
                output_path=str(output_path),
                old_text=request.old_text,
                new_text=request.new_text
            )

        else:
            raise ValueError(
                "Editing is currently supported only for XLSX and DOCX."
            )

        return {
            "workspace_id": workspace_id,
            "file_id": file_id,
            "result": result
        }

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )