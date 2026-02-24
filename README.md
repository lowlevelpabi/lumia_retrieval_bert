# SMART RESEARCH: AI-Powered Research Paper Retrieval

### (BERT-NLP Backend Prototype)

This is a specialized backend for a Research Paper Retrieval and Recommendation System. It uses **BERT-NLP** (via Sentence-Transformers) and a vector database (**Qdrant**) to provide semantic search based on paper abstracts and titles.

---

## 🚀 Core Features

- **Hybrid Retrieval System**: Combines SQL keyword matching (for 100% term accuracy) with BERT-powered semantic search (for contextual understanding).
- **Role-Based Access Control (RBAC)**: Tiered privilege system for **Admin**, **Faculty**, and **User** roles protected by JWT authentication.
- **Advanced Academic Filtering**: Filter research papers by Year Range (Last 5 years), Department, Author, and citation metrics.
- **"Narrow Down" Recommendations**: Context-aware recommendation engine that finds similar studies within specific metadata constraints.
- **Intelligent Metadata Extraction**: Automatically detects Title, Author, Year, Department, Degree Program, and Abstract from PDFs using OCR.
- **Multi-Vector Semantic Indexing**: Independently indexes Titles and Abstracts in **Qdrant** for maximum retrieval precision.
- **Enhanced Upload Flow**: Guided 3-step upload with Smart Extract (OCR) or Manual Review strategy selection and page thumbnail previews.
- **RESTful API**: Professional CRUD operations for paper management and academic discovery.

---

## 🛠 Tech Stack

- **Framework**: FastAPI (Python)
- **AI/NLP**: Sentence-Transformers (`multi-qa-MiniLM-L6-cos-v1`)
- **Vector DB**: Qdrant (Local Storage Mode)
- **Relational DB**: SQLite (Metadata storage)
- **OCR**: Pypdf, Pytesseract, Poppler

---

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

---

## 📁 Project Structure

- `app/api/endpoints/`: API route definitions.
- `app/services/`: Core logic for OCR, Embeddings, and Vector Search.
- `app/models/`: Database schemas.
- `uploads/`: Physical storage for uploaded PDFs.
- `qdrant_storage/`: Local vector database files.
- `history/`: Sprint run logs (see below).

---

## 📋 Sprint History

> Full week-by-week sprint details are documented in:
> **[`history/sprint_history.txt`](./history/sprint_history.txt)**

This project uses a **non-fixed sprint structure** due to iterative clarification with the thesis adviser. All development phases are part of **Sprint 2**.

---

## 📜 Changelog

### Sprint 2 – Week C _(2026-02-25)_

_OCR Accuracy, Author Detection & Upload UI Refinement_

- **Author Detection Fix**: Replaced all previous heuristics with `re.findall()` directly on raw cover-page text, using Filipino academic name patterns (`SURNAME, FIRSTNAME M.I.` — both ALL CAPS and Title Case).
- **Author Delimiter Fix**: Changed join/split delimiter from `,` to `|` to prevent Filipino-format names (which contain commas) from being broken into separate fields.
- **Descriptive Fallbacks**: Author and abstract fields now show instructional messages when data cannot be auto-detected, consistent across Smart Extract and Manual Review modes.
- **Vertical Step Navigation**: Upload step indicator moved to a fixed right-side vertical rail with a pulse effect on the active step.
- **Header Layout Fix**: Long paper filenames now truncate with ellipsis, preventing layout overlap.
- **Abstract Cleanup**: Removed cover-page fallback that incorrectly populated the abstract with table-of-contents text.

---

### Sprint 2 – Week B

_Upload Flow UX Overhaul & Thumbnail Previews_

- **3-Step Upload Flow**: Strategy selection → Metadata review → Confirmation.
- **Smart/Manual Strategy**: Users choose between OCR auto-extraction or manual input.
- **PDF Page Thumbnails**: Live page previews with zoom modal and side-by-side extracted text.
- **Page Selection**: Users select which pages to vectorize, excluding noise pages.
- **Step Indicator**: Visual progress indicator across the upload flow.
- **Department Detection Refinement**: Degree-to-department inference fallback added.

---

### Sprint 2 – Week A

_Advanced Retrieval, RBAC & Academic Categorization_

- **RBAC**: Admin / Faculty / User roles with JWT + bcrypt authentication.
- **Hybrid Search**: SQL `LIKE` keyword matching + BERT semantic scoring.
- **Advanced Filters**: Author, year range, department, degree program, project type.
- **"Narrow Down" Recommendations**: Qdrant-powered context-aware discovery.
- **Citation & View Count**: Added metrics seeding for realistic paper statistics.
- **Degree/Project Detection**: OCR auto-detects BSCS, BSIT, BSIS, BSCpE and classifies Capstone vs Thesis.

---

### Sprint 1 – Foundational MVP

_AI-Powered PDF Archive Foundation_

- **BERT-NLP Integration**: Sentence-Transformers semantic embeddings.
- **Vector Database**: Qdrant for nearest-neighbor retrieval.
- **OCR Pipeline**: Multi-stage extraction using `pypdf` and `Tesseract`.
- **Relational Metadata**: SQLite/SQLAlchemy for persistent storage.
- **Core API**: Upload and semantic discovery endpoints.
- **DevOps**: Docker and PowerShell setup scripts.

---

## 📝 License

Proprietary Prototype for Undergrad Thesis research.
