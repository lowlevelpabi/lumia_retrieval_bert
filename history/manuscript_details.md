# LUMIA: Thesis Manuscript Details (Ready for Copy-Paste)

> [!TIP]
> **Green Sections [FINAL]**: These are ready to be copied into your manuscript as is.
> **Yellow Sections [PENDING DATA]**: These describe the *plan*. You can copy them now, but you must update the bracketed parts once you have your results.

---

## 1. Research Design [STATUS: FINAL]
The study employed a **Developmental Research design**, focusing on the systematic design, development, and evaluation of an AI-powered research paper retrieval system. The development process followed an **Agile Iterative methodology**, characterized by a **four-sprint development cycle** followed by a formal evaluation phase. This structure allowed for initial requirement discovery, followed by iterative technical implementation and refinement based on academic feedback. The project progressed from initial roadmap planning and data gathering into the technical construction of the BERT-NLP architecture, multi-vector semantic indexing in **Qdrant**, and a **Hybrid Search engine** combining SQL keyword matching with semantic scoring.

---

## 2. Research Approach [STATUS: FINAL]
The study adopts a **mixed-methods approach** to evaluate the system’s performance. The **quantitative component** assesses technical accuracy through Information Retrieval (IR) metrics, specifically measuring the precision and recall of the BERT-powered similarity search. It also records performance data such as OCR extraction speed and vector retrieval response times. The **qualitative component** involves gathering descriptive feedback from targeted user testing (IT Experts and Students) to refine the system’s interface ergonomics, the accuracy of its **Intelligent Metadata Extraction**, and the relevance of its IMRAD-aware recommendation engine.

---

## 3. Research Settings [STATUS: FINAL]
The study is conducted at **Cavite State University - Imus Campus (CvSU-Imus)**. This location was chosen as the primary environment for data gathering and system implementation, leveraging the campus's localized academic workflow and document standards for undergraduate thesis management.

---

## 4. Participants / Respondents / Data Sources [STATUS: PENDING DATA]
*   **Data Source [FINAL]:** The primary dataset consists of the official repository of undergraduate thesis documents from the **CvSU-Imus Department of Computer Science**, specifically focusing on metadata, abstracts, and full-text IMRAD sections from previously graduated students.
*   **Respondents [PENDING]:** The system evaluation includes two primary groups:
    *   **IT Experts:** Five (5) specialists in information technology and software engineering were selected to evaluate technical quality and architecture.
    *   **End-Users:** A targeted sample of **50 evaluators**, consisting of students and faculty members from the Department of Computer Science. 
    *   > [!NOTE]
        > *Once data is collected, you can add: "The final respondent pool consisted of [X] males and [Y] females..."*

---

## 5. Research Instruments [STATUS: FINAL]
To capture both technical and user-centric data, the researchers developed a comprehensive set of research instruments. A **Software Quality Evaluation Form**, structured as a Likert-scale instrument based on ISO/IEC 25010 standards, is utilized to gather feedback from both IT experts and end-users regarding the system's functionality, reliability, and usability. Complementing this, an **Accuracy Testing Log** serves as a technical ledger to record the performance of the integrated **IMRAD Detection Service**, allowing for the systematic tracking of the model's ability to classify academic chapters into semantic categories. Finally, a **User Feedback Questionnaire** was implemented during the pre-survey and testing phases to gather qualitative insights into feature requirements and the relevance of the recommendation engine, ensuring that specific user suggestions were integrated into the development iterations.

---

## 6. Data Collection Procedure [STATUS: FINAL]
The data collection procedure followed a structured, multi-stage lifecycle beginning with the **Pre-Survey and Analysis** phase, where the researchers engaged with potential respondents to identify critical system features and assess the potential impact of the platform on academic research workflows. This was followed by the **Data Gathering** stage, involving the collection and digitization of past undergraduate thesis papers from the Department of Computer Science repository. In the **Extraction and Vectorization** phase, the collected documents were processed through the system's **Smart Extract** pipeline using Tesseract OCR and PyMuPDF to transform raw text into 384-dimensional dense vectors for high-speed indexing in the **Qdrant** database. The procedure concluded with **Controlled Testing** sessions, where iterative debugging and retrieval accuracy assessments were performed to stabilize the system before final evaluation.

---

## 7. Data Analysis Techniques [STATUS: PENDING DATA]
*   **Usability Analysis [FINAL]:** User satisfaction and usability ratings are interpreted using the **Statistical Mean**. A scale of 1 to 5 is used to determine the level of acceptability. 
*   **Technical Performance [PENDING]:** Technical performance is analyzed using **Information Retrieval Metrics**, focusing on **Precision and Recall**. 
*   > [!IMPORTANT]
    > *Placeholder for Results: "Based on the testing logs, the system achieved an average precision of [X%] and a recall of [Y%] during semantic search evaluations."*

---

## 8. Ethical Considerations [STATUS: FINAL]
The researchers prioritized **Intellectual Property protection** by implementing a Role-Based Access Control (RBAC) system that limits full-text access according to university guidelines. **Confidentiality** is maintained by anonymizing all user testing data, and **Informed Consent** was obtained from all participants prior to evaluation sessions, ensuring that participation was voluntary.

---

## 9. Development Model (Agile Iterative Model) [STATUS: MIXED]
The development of the system followed an **Agile Iterative Model**, structured into four distinct sprints leading toward a final evaluation phase. **Sprint 1 (Planning and Discovery)** focused on the comprehensive identification of research methods, technical approaches, and the overall project roadmap. This was followed by **Sprint 2 (Requirement Gathering & Data Collection)**, which involved conducting pre-surveys to define essential features and gathering past thesis documents from department graduates. The project then transitioned into **Sprint 3 (System Development)**, the core implementation phase where the BERT-NLP architecture, Qdrant vector database, and FastAPI backend were constructed. The cycle continued with **Sprint 4 (Testing and Iterative Refinement)**, dedicated to identifying and resolving technical bugs while improving system stability based on internal testing results. Upon completion of these cycles, the project enters the **Evaluation Phase**, where five IT experts and fifty targeted respondents perform a formal assessment of the system's quality and research utility.

---

### Key Technical Specs [STATUS: FINAL]
| Component | Details |
| :--- | :--- |
| **Model** | `multi-qa-MiniLM-L6-cos-v1` (Sentence-Transformers) |
| **Vector DB** | Qdrant (Local Storage Mode) |
| **Backend** | FastAPI (Python) |
| **Frontend** | Vue.js 3 / Vite |
| **Search Engine** | Hybrid (SQL Keyword + Semantic) |
| **Architecture** | IMRAD Section-Aware Multi-Vector Retrieval |
