# SMART RESEARCH: AI-Powered Research Paper Retrieval

### (BERT-NLP Backend Prototype)

This is a specialized backend for a Research Paper Retrieval and Recommendation System. It uses **BERT-NLP** (via Sentence-Transformers) and a vector database (**Qdrant**) to provide semantic search based on paper abstracts and titles.

## 🚀 Core Features

- **Hybrid Retrieval System**: Combines SQL keyword matching (for 100% term accuracy) with BERT-powered semantic search (for contextual understanding).
- **Role-Based Access Control (RBAC)**: Tiered privilege system for **Admin**, **Faculty**, and **User** roles protected by JWT authentication.
- **Advanced Academic Filtering**: Filter research papers by Year Range (Last 5 years), Department, Author, and citation metrics.
- **"Narrow Down" Recommendations**: Context-aware recommendation engine that finds similar studies within specific metadata constraints.
- **Intelligent Metadata Extraction**: Automatically detects Title, Author, Year, Department, and Abstract from PDFs using OCR and regex heuristics.
- **Multi-Vector Semantic Indexing**: Independently indexes Titles and Abstracts in **Qdrant** for maximum retrieval precision.
- **RESTful API**: Professional CRUD operations for paper management and academic discovery.

## 🛠 Tech Stack

- **Framework**: FastAPI (Python)
- **AI/NLP**: Sentence-Transformers (`multi-qa-MiniLM-L6-cos-v1`)
- **Vector DB**: Qdrant (Local Storage Mode)
- **Relational DB**: SQLite (Metadata storage)
- **OCR**: Pypdf, Pytesseract, Poppler

## ⚙️ Installation (Windows)

### 1. Prerequisites

You must install these external tools on your system and add them to your PATH:

- **Tesseract OCR**: [Download](https://github.com/UB-Mannheim/tesseract/wiki)
- **Poppler**: [Download Library](https://github.com/oschwartz10612/poppler-windows/releases/)

### 2. Setup Environment

Open PowerShell in the project root:

```powershell
./setup_local.ps1
```

_This script creates the virtual environment and installs all Python dependencies._

### 3. Start the Server

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.
You can access the interactive documentation (Swagger) at `http://127.0.0.1:8000/docs`.

## 📁 Project Structure

- `app/api/endpoints/`: API route definitions.
- `app/services/`: Core logic for OCR, Embeddings, and Vector Search.
- `app/models/`: Database schemas.
- `uploads/`: Physical storage for uploaded PDFs.
- `qdrant_storage/`: Local vector database files.

## 📜 Changelog

### Sprint 2: Advanced Retrieval & Role Management

- **Role-Based Access Control (RBAC)**: Implemented `Admin`, `Faculty`, and `User` roles with JWT protection.
- **Hybrid Search Engine**: Combined SQL keyword matching with BERT semantic scoring.
- **Direct Bcrypt Security**: Optimized password hashing for Python 3.13 stability.
- **Advanced Metadata**: Added support for `citation_count`, `department`, and `keywords`.
- **Filtered Recommendations**: Implemented "Narrow Down" logic for context-specific discovery.
- **OCR Upgrades**: Enhanced auto-detection of departments and research keywords.
- **Improved Recall**: Adjusted similarity threshold to 0.2 for broader discovery.

### Sprint 1: Foundational MVP & Semantic Search

- **BERT-NLP Integration**: Implemented Sentence-Transformers for semantic embeddings.
- **Vector Database**: Configured Qdrant for high-speed nearest-neighbor retrieval.
- **OCR Pipeline**: Multi-stage extraction using `pypdf` and `Tesseract`.
- **Relational Metadata**: SQLite/SQLAlchemy integration for persistent storage.
- **Core API**: Developed primary endpoints for upload and semantic discovery.
- **DevOps**: Established Docker and PowerShell setup scripts for portability.

## 📝 License

Proprietary Prototype for Undergrad Thesis research.
