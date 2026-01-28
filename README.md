# SMART RESEARCH: AI-Powered Research Paper Retrieval

### (BERT-NLP Backend Prototype)

This is a specialized backend for a Research Paper Retrieval and Recommendation System. It uses **BERT-NLP** (via Sentence-Transformers) and a vector database (**Qdrant**) to provide semantic search based on paper abstracts and titles.

## 🚀 Core Features

- **Intelligent Metadata Extraction**: Automatically detects Title, Author, Year, and Abstract from uploaded PDFs (priority to text extraction, fallback to Tesseract OCR).
- **Multi-Vector Semantic Search**: Independently indexes Titles and Abstracts to ensure high-accuracy search results and relevant scoring.
- **Similarity Thresholding**: Filters out irrelevant results to maintain a professional citation/recommendation standard.
- **RESTful API**: Full CRUD capabilities for paper management (Upload, Search, Update, Delete).

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

## 📝 License

Proprietary Prototype for Undergrad Thesis research.
