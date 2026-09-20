import json
from pathlib import Path

import faiss
from sentence_transformers import SentenceTransformer


EMBEDDING_MODEL = "all-MiniLM-L6-v2"

_model = SentenceTransformer(EMBEDDING_MODEL)


def load_parsed_file(parsed_path: str) -> dict:
    with open(parsed_path, "r", encoding="utf-8") as f:
        return json.load(f)


def create_chunks(parsed_data: dict, chunk_size: int = 1000):
    """
    Convert parsed document content into searchable chunks.
    """

    chunks = []

    file_type = parsed_data["file_type"]
    filename = parsed_data["filename"]

    # PDF
    if file_type == "pdf":

        for page in parsed_data["pages"]:

            text = page["text"]

            for i in range(0, len(text), chunk_size):

                chunk_text = text[i:i + chunk_size].strip()

                if chunk_text:
                    chunks.append({
                        "text": chunk_text,
                        "filename": filename,
                        "page": page["page_number"]
                    })

    # DOCX
    elif file_type == "docx":

        for index, text in enumerate(
            parsed_data["paragraphs"]
        ):

            if text.strip():

                chunks.append({
                    "text": text,
                    "filename": filename,
                    "paragraph": index + 1
                })

    # XLSX
    elif file_type == "xlsx":

        for sheet_name, sheet_data in parsed_data["sheets"].items():

            rows = sheet_data["rows"]

            for row_number, row in enumerate(rows, start=1):

                text = " | ".join(
                    f"{key}: {value}"
                    for key, value in row.items()
                )

                chunks.append({
                    "text": text,
                    "filename": filename,
                    "sheet": sheet_name,
                    "row": row_number
                })

    # CSV
    elif file_type == "csv":

        for row_number, row in enumerate(
            parsed_data["rows"],
            start=1
        ):

            text = " | ".join(
                f"{key}: {value}"
                for key, value in row.items()
            )

            chunks.append({
                "text": text,
                "filename": filename,
                "row": row_number
            })

    return chunks


def build_index(
    chunks: list,
    index_path: str,
    metadata_path: str
):
    """
    Create FAISS vector index from document chunks.
    """

    if not chunks:
        raise ValueError("No chunks available for indexing.")

    texts = [
        chunk["text"]
        for chunk in chunks
    ]

    embeddings = _model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    dimension = embeddings.shape[1]

    index = faiss.IndexFlatIP(dimension)

    index.add(embeddings)

    index_path = Path(index_path)
    metadata_path = Path(metadata_path)

    index_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    faiss.write_index(
        index,
        str(index_path)
    )

    with open(
        metadata_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            chunks,
            f,
            indent=2,
            ensure_ascii=False
        )


def search(
    query: str,
    index_path: str,
    metadata_path: str,
    top_k: int = 5
):
    """
    Search the FAISS index for relevant chunks.
    """

    index = faiss.read_index(
        str(index_path)
    )

    with open(
        metadata_path,
        "r",
        encoding="utf-8"
    ) as f:

        chunks = json.load(f)

    query_embedding = _model.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    scores, indices = index.search(
        query_embedding,
        min(top_k, len(chunks))
    )

    results = []

    for score, index_id in zip(
        scores[0],
        indices[0]
    ):

        if index_id < 0:
            continue

        result = chunks[index_id].copy()

        result["score"] = float(score)

        results.append(result)

    return results