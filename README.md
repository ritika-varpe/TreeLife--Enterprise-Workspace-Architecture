# Treelife AI — Persistent Document Workspace

A lightweight persistent AI workspace built for the Treelife AI Engineer Technical Assessment.

The system allows users to upload multiple documents into a persistent workspace, process each document once, build a searchable vector index, ask questions across documents using AWS Bedrock + Gemma, and generate validated modifications to Excel and Word files.

---

## 1. Objective

The goal is to build a persistent AI workspace instead of treating every interaction as an independent chat session.

The system follows:

```text
Upload Once
    ↓
Parse Once
    ↓
Chunk + Index
    ↓
Retrieve Relevant Context
    ↓
Ask Gemma
    ↓
Return Grounded Answer

For document modifications:

User Request
    ↓
LLM / Structured Instructions
    ↓
Python File Engine
    ↓
Modify Existing File
    ↓
Validate
    ↓
Generated Output
2. Key Features
Persistent workspace creation
Multiple file upload
SHA-256 duplicate detection
PDF, DOCX, XLSX and CSV parsing
Document chunking
Embedding generation
FAISS vector indexing
Cross-document semantic search
AWS Bedrock + Google Gemma
Source-aware answers
Excel file modification using openpyxl
Word file modification using python-docx
Generated file validation
Persistent parsed/indexed/output artifacts
3. Supported File Types
File Type	Parser / Tool	Processing
PDF	PyMuPDF	Page-level text extraction
DOCX	python-docx	Paragraph and table extraction
XLSX	pandas / openpyxl	Sheet, column and row extraction
CSV	pandas	Structured row/column extraction

Excel and CSV files are handled as structured data instead of treating them as plain text.

4. Architecture
                         USER
                           |
                           v
                    +--------------+
                    |   FastAPI    |
                    +------+-------+
                           |
              +------------+-------------+
              |                          |
              v                          v
         File Upload                 Query
              |                          |
              v                          v
        SHA-256 Check               FAISS Search
              |                          |
       +------+-------+                  |
       |              |                  v
   Duplicate        New File       Relevant Chunks
       |              |                  |
       |              v                  v
       |           Parser             Gemma
       |              |             AWS Bedrock
       |              v                  |
       |           Chunks                v
       |              |               Answer
       |              v
       |          Embeddings
       |              |
       |              v
       |           FAISS
       |
       v
     Skip
5. Project Structure
treelife-ai-workspace/
│
├── app.py
├── ingest.py
├── parser.py
├── retrieve.py
├── llm.py
├── file_editor.py
│
├── data/
│   ├── registry.json
│   └── workspaces/
│       └── <workspace_id>/
│           ├── workspace.json
│           ├── files/
│           ├── parsed/
│           ├── index/
│           └── outputs/
│
├── .env
├── .gitignore
├── requirements.txt
└── README.md
6. Persistent Workspace

Every workspace has its own persistent directory.

Example:

data/
└── workspaces/
    └── <workspace_id>/
        ├── files/
        ├── parsed/
        ├── index/
        ├── outputs/
        └── workspace.json

The workspace shown during testing contains the following generated artifacts:

files/
index/
outputs/
parsed/
workspace.json

This demonstrates that uploaded documents, parsed representations, vector indexes and generated outputs are persisted independently.

Workspace storage evidence

The repository includes a screenshot showing the actual generated workspace directory after processing and file modification.

The directories represent:

Directory	Purpose
files/	Original uploaded documents
parsed/	Parsed document JSON
index/	FAISS indexes and chunk metadata
outputs/	Generated/modified documents
workspace.json	Workspace and file metadata
7. File Registry

A global registry.json maintains SHA-256 based file information.

Example structure:

{
    "<sha256_hash>": {
        "workspace_id": "<workspace_id>",
        "file_id": "<file_id>",
        "filename": "document.pdf",
        "file_type": ".pdf",
        "processed": true
    }
}

The registry allows the system to determine whether the exact same file content has already been processed.

8. Duplicate Detection

Every uploaded file is hashed using SHA-256.

File
 ↓
SHA-256
 ↓
Registry Lookup
 ↓
Already Exists?
 ├── YES → Skip processing
 └── NO  → Process document

For example, uploading the same PDF twice results in:

{
    "status": "duplicate",
    "message": "File already processed. Skipping ingestion."
}

This prevents unnecessary parsing, embedding generation and indexing.

9. Document Processing Pipeline

A new document follows this pipeline:

Uploaded File
     ↓
SHA-256
     ↓
Duplicate Check
     ↓
Save Original File
     ↓
Parser
     ↓
Parsed JSON
     ↓
Chunking
     ↓
Embeddings
     ↓
FAISS Index

For example, a PDF follows:

PDF
 ↓
PyMuPDF
 ↓
Pages
 ↓
Text
 ↓
Chunks
 ↓
Embeddings
 ↓
FAISS

The parsed representation is stored under:

data/workspaces/<workspace_id>/parsed/
10. Vector Search

The system uses FAISS for local vector retrieval.

Each document is split into searchable chunks.

Document
    ↓
Chunks
    ↓
Embedding Model
    ↓
Vectors
    ↓
FAISS

The index and chunk metadata are stored under:

data/workspaces/<workspace_id>/index/

The chunk metadata allows the system to retain information such as:

Filename
Page number
Sheet name
Row number
Chunk text
11. Retrieval-Augmented Generation

When a user asks a question, the system does not send the entire workspace to the LLM.

Instead:

User Question
      ↓
FAISS Search
      ↓
Top-K Relevant Chunks
      ↓
Context Construction
      ↓
Gemma via AWS Bedrock
      ↓
Answer + Sources

Example:

50 uploaded documents
        ↓
Semantic retrieval
        ↓
Top 5 relevant chunks
        ↓
Gemma

This reduces unnecessary prompt size and keeps the model focused on relevant information.

12. Cross-Document Queries

The query endpoint searches across all processed documents within the workspace.

For example:

Compare the revenue reported in the annual report
with the revenue in the financial spreadsheet.

The system:

Searches the indexes of processed documents.
Retrieves the highest-ranking chunks.
Combines the relevant context.
Sends only that context to Gemma.
Returns the answer with source information.
13. Excel Processing

Excel files are not treated as plain text.

The processing flow is:

Excel Workbook
      ↓
Sheets
      ↓
Columns / Rows
      ↓
Structured Records
      ↓
Searchable Chunks

Example metadata:

{
    "filename": "financials.xlsx",
    "sheet": "Revenue",
    "row": 12,
    "text": "Year: 2025 | Region: India | Revenue: 1500000"
}

This preserves spreadsheet structure during retrieval.

For numerical operations, the implementation can be extended to perform deterministic pandas calculations rather than relying entirely on LLM reasoning.

14. LLM — AWS Bedrock + Gemma

The system uses Google Gemma through AWS Bedrock.

Configuration is controlled through environment variables:

AWS_REGION=your-region
BEDROCK_MODEL_ID=your-gemma-model-id

CHUNK_SIZE=1000
CHUNK_OVERLAP=150

TOP_K=5

MAX_TOKENS=1024
TEMPERATURE=0.0

AWS credentials are not stored in the repository.

The application uses the configured AWS environment/IAM credentials to access Bedrock.

15. File Modification

The LLM does not directly create or manipulate binary files.

Instead:

User Request
      ↓
Structured Instruction
      ↓
Python File Engine
      ↓
openpyxl / python-docx
      ↓
Validation
      ↓
Output File
Example Excel instruction
{
    "operation": "update_cell",
    "sheet": "Revenue",
    "cell": "D12",
    "value": 1500000
}

Python then performs the actual modification using openpyxl.

Example Word operation
{
    "operation": "replace_text",
    "old_text": "Old Company Name",
    "new_text": "New Company Name"
}

The modified file is saved under:

data/workspaces/<workspace_id>/outputs/
16. Output Validation

Generated files are validated after modification.

For Excel:

Modified XLSX
     ↓
Open with openpyxl
     ↓
Validate workbook
     ↓
Validate sheet
     ↓
Validate modified cell
     ↓
Save final output

For Word:

Modified DOCX
     ↓
Open with python-docx
     ↓
Validate replacement
     ↓
Save final output

This ensures that the LLM is not responsible for constructing the final binary document.

17. API Endpoints
Health Check
GET /health
Create Workspace
POST /workspace?name=MyWorkspace
Get Workspace
GET /workspace/{workspace_id}
Upload Files
POST /workspace/{workspace_id}/upload

Supports multiple files.

Query Workspace
POST /workspace/{workspace_id}/query

Example:

{
    "question": "What is the objective of this assessment?",
    "top_k": 5
}
Edit File
POST /workspace/{workspace_id}/edit/{file_id}

Example:

{
    "operation": "update_cell",
    "sheet": "Revenue",
    "cell": "D12",
    "value": 1500000
}
18. Running the Application

Install dependencies:

pip install -r requirements.txt

Configure AWS credentials using the local AWS environment/IAM setup.

Create .env:

AWS_REGION=your-region
BEDROCK_MODEL_ID=your-gemma-model-id

CHUNK_SIZE=1000
CHUNK_OVERLAP=150
TOP_K=5
MAX_TOKENS=1024
TEMPERATURE=0.0

Start the server:

uvicorn app:app --reload

Open Swagger UI:

http://127.0.0.1:8000/docs
19. Example End-to-End Workflow
Step 1 — Create workspace
POST /workspace
Step 2 — Upload documents
POST /workspace/{workspace_id}/upload

Example files:

annual_report.pdf
financials.xlsx
company_notes.docx
data.csv
Step 3 — Automatic processing
Upload
  ↓
Hash
  ↓
Parse
  ↓
Chunk
  ↓
Embed
  ↓
FAISS Index
Step 4 — Ask a question
POST /workspace/{workspace_id}/query
Step 5 — Retrieve relevant information
Question
  ↓
FAISS
  ↓
Relevant chunks
Step 6 — Generate answer
Relevant chunks
  ↓
Gemma / Bedrock
  ↓
Grounded answer
Step 7 — Modify a document
POST /workspace/{workspace_id}/edit/{file_id}
Step 8 — Validate and save
Python File Engine
       ↓
Validation
       ↓
outputs/
20. Design Decisions
Local filesystem

Local filesystem storage was selected for the assessment to keep the implementation simple and self-contained.

A production implementation could replace this with S3 and a persistent database.

FAISS

FAISS provides lightweight local vector search without requiring an external vector database.

SHA-256

SHA-256 provides a simple content-based mechanism for identifying files that have already been processed.

Bedrock + Gemma

AWS Bedrock provides the model execution layer while keeping the model configuration outside the application logic.

Deterministic file editing

The LLM is used for reasoning and structured instructions.

Python libraries perform the actual file modification and validation.

21. Token Efficiency

The system is designed around selective retrieval.

Instead of:

50 Documents
     ↓
LLM

the system performs:

50 Documents
     ↓
FAISS Retrieval
     ↓
Top-K Chunks
     ↓
LLM

Therefore, the LLM only receives the relevant context required for the current question.

The values can be tuned through:

CHUNK_SIZE=1000
CHUNK_OVERLAP=150
TOP_K=5
MAX_TOKENS=1024
22. Current Limitations

This implementation is intentionally lightweight for the technical assessment.

Current limitations:

Local filesystem storage
Local FAISS indexes
No background processing queue
Limited document editing operations
Word replacement is limited when text is distributed across multiple document runs
No authentication/authorization layer
No production-grade concurrency handling
Scanned/image-only PDFs require an OCR pipeline
Spreadsheet numerical reasoning can be further extended with deterministic pandas operations
23. Production Extensions

A production version could extend the architecture with:

                    API
                     |
                     v
                  S3 Storage
                     |
                     v
              Processing Queue
                     |
          +----------+----------+
          |                     |
          v                     v
      PDF/DOCX              XLSX/CSV
       Parser               Processor
          |                     |
          +----------+----------+
                     |
                     v
                 Embeddings
                     |
                     v
              Vector Database
                     |
                     v
               Query Planner
                /         \
               /           \
        Vector Search    Table/SQL
               \           /
                \         /
                     v
                Gemma / LLM
                     |
                     v
             Validated Output
24. Summary

The implementation demonstrates a persistent AI workspace with the following core principles:

Store once
    ↓
Process once
    ↓
Index once
    ↓
Retrieve selectively
    ↓
Reason using relevant context
    ↓
Modify files deterministically
    ↓
Validate generated outputs

The implementation focuses on demonstrating the core workflow required by the assessment while keeping the architecture lightweight and easy to run locally.


### One small GitHub recommendation

For the screenshot, put the image in your repository like:

```text
── workspace-storage.png

Then this README line will work:

![Workspace Storage](docs/workspace-storage.png)

## Architecture

![Architecture](docs/architecture.png)
