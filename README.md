# TN Insight AI

### Citation-Grounded Government Document Intelligence Platform

TN Insight AI is a full-stack AI-powered document intelligence platform designed to help users understand, search, compare, and analyze complex government and legal documents.

Instead of relying only on general-purpose AI responses, the system uses a custom **TF-IDF + BM25 hybrid retrieval pipeline** to identify relevant sections of uploaded PDFs before generating an answer. Responses are grounded in retrieved document content and include **page-level source references** for verification.

---

## Key Features

- **AI-Powered Document Q&A** – Ask natural-language questions about uploaded PDFs and receive document-grounded answers.
- **Hybrid Information Retrieval** – Combines TF-IDF and BM25 ranking to retrieve relevant document chunks.
- **Source-Page Citations** – AI responses include clickable page references for verification against the original PDF.
- **PDF Processing & OCR** – Extracts content from digital PDFs and supports scanned documents through OCR.
- **Bilingual Analysis** – Generate responses in English or Tamil.
- **Document Comparison** – Upload and compare two government/legal documents using AI.
- **Private Document Library** – Authenticated users can save, load, manage, and delete their own documents.
- **User Authentication** – Secure registration and login with token-based authentication.
- **Quick Analysis Actions** – One-click prompts for summaries, eligibility requirements, deadlines, and required documents.
- **Light & Dark Themes** – Modern responsive interface with persistent theme preference.
- **Retrieval Evaluation** – Evaluates search quality using Recall@K and Mean Reciprocal Rank (MRR).

---

## System Architecture

```text
                     ┌─────────────────────┐
                     │       User          │
                     └──────────┬──────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │   React Frontend    │
                     │      Vercel         │
                     └──────────┬──────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │  FastAPI Backend    │
                     │       Render        │
                     └──────────┬──────────┘
                                │
                         PDF Upload
                                │
                                ▼
                     ┌─────────────────────┐
                     │ Text Extraction /   │
                     │        OCR          │
                     └──────────┬──────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │ Document Chunking   │
                     └──────────┬──────────┘
                                │
                 ┌──────────────┴──────────────┐
                 ▼                             ▼
        ┌─────────────────┐          ┌─────────────────┐
        │     TF-IDF      │          │      BM25       │
        │    Retrieval    │          │    Retrieval    │
        └────────┬────────┘          └────────┬────────┘
                 └──────────────┬──────────────┘
                                ▼
                     ┌─────────────────────┐
                     │   Hybrid Ranking    │
                     └──────────┬──────────┘
                                │
                         Relevant Chunks
                                │
                                ▼
                     ┌─────────────────────┐
                     │   LLM Generation    │
                     └──────────┬──────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │ Answer + Source     │
                     │ Page Citations      │
                     └─────────────────────┘
```

---

## Hybrid Retrieval Pipeline

TN Insight AI implements a custom lexical retrieval pipeline rather than sending the complete document directly to the language model.

### 1. PDF Processing

Uploaded PDFs are processed to extract page-wise text. OCR support is used when necessary for scanned documents.

### 2. Document Chunking

Extracted text is divided into overlapping chunks while preserving the corresponding page numbers.

### 3. TF-IDF Retrieval

The system creates TF-IDF representations using unigrams and bigrams and calculates cosine similarity between the user's query and document chunks.

### 4. BM25 Retrieval

BM25 independently ranks document chunks based on lexical relevance to the query.

### 5. Hybrid Ranking

Normalized TF-IDF and BM25 scores are combined:

```text
Hybrid Score =
0.45 × TF-IDF Score +
0.55 × BM25 Score
```

The highest-ranking chunks are provided as evidence to the answer-generation layer.

### 6. Citation-Grounded Generation

The AI generates an answer using the retrieved context and returns the relevant PDF page numbers, allowing users to verify information against the original document.

---

## Retrieval Evaluation

The retrieval system is evaluated separately from answer generation using a manually prepared question-to-relevant-page evaluation dataset.

Metrics include:

- Recall@1
- Recall@3
- Recall@5
- Mean Reciprocal Rank (MRR)

### Current Evaluation Results

| Retriever | Recall@1 | Recall@3 | Recall@5 | MRR |
|---|---:|---:|---:|---:|
| TF-IDF | 0.60 | 1.00 | 1.00 | 0.80 |
| BM25 | 0.70 | 1.00 | 1.00 | 0.85 |
| Hybrid | **0.70** | **1.00** | **1.00** | **0.85** |

> These results are based on the project's current 10-question evaluation dataset and should not be interpreted as performance across all government or legal documents.

---

## Technology Stack

### Frontend

- React.js
- Vite
- Tailwind CSS
- Lucide React
- Axios
- React PDF
- PDF.js

### Backend

- Python
- FastAPI
- Uvicorn
- SQLAlchemy
- SQLite

### Information Retrieval & AI

- TF-IDF
- BM25
- Cosine Similarity
- Scikit-learn
- Rank-BM25
- OpenRouter API
- Retrieval-Augmented Generation (RAG)

### Document Processing

- PyMuPDF
- OCR / Tesseract
- PDF text extraction

### Deployment

- Vercel – Frontend
- Render – Backend
- GitHub – Version control

---

## Project Structure

```text
TN-Insight-AI/
│
├── backend/
│   ├── main.py
│   ├── database.py
│   ├── library.py
│   ├── pdf_utils.py
│   ├── rag.py
│   ├── evaluation.py
│   ├── evaluation_dataset.json
│   └── requirements.txt
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── index.css
│   │   └── main.jsx
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
│
├── .gitignore
└── README.md
```

---

## Running Locally

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd TN-Insight-AI
```

### 2. Backend Setup

```bash
cd backend
python -m venv venv
```

Activate the virtual environment.

Windows:

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file inside `backend/` and configure the required environment variables:

```env
OPENROUTER_API_KEY=your_openrouter_api_key
AUTH_SECRET_KEY=your_secure_secret_key
```

Start FastAPI:

```bash
python -m uvicorn main:app --port 8001
```

The backend will run locally at:

```text
http://127.0.0.1:8001
```

### 3. Frontend Setup

Open another terminal:

```bash
cd frontend
npm install
```

Create `.env.local` if required:

```env
VITE_API_BASE_URL=http://127.0.0.1:8001
```

Start the frontend:

```bash
npm run dev
```

---

## Security

Sensitive credentials are stored using environment variables and are excluded from Git through `.gitignore`.

The repository should never contain:

```text
.env
.env.local
API keys
authentication secrets
local databases
uploaded private documents
```

User document-library operations are protected through authenticated requests.

---

## Example Use Cases

TN Insight AI can be used to analyze documents such as:

- Government Orders
- Government schemes and notifications
- Policy documents
- Administrative orders
- Circulars
- Court judgments and orders
- Public notices
- Departmental documents
- Regulatory documents

Example questions include:

```text
"What is the administrative sanction amount?"

"What are the eligibility requirements?"

"What is the final decision in this judgment?"

"Which department issued this order?"

"What deadlines are mentioned?"

"Summarize this document in simple language."
```

---

## TN Insight AI vs General-Purpose AI Assistants

TN Insight AI is not intended to replace general-purpose AI assistants. It provides a specialized workflow for government and legal document intelligence.

Its primary differentiators include:

- Custom TF-IDF + BM25 retrieval
- Configurable hybrid ranking
- Quantitative retrieval evaluation
- Page-level evidence verification
- Private authenticated document libraries
- Government/legal-document-focused workflows
- Cross-document comparison
- Bilingual document analysis
- Organization-controlled backend and retrieval pipeline

This provides greater control over how documents are processed, retrieved, ranked, evaluated, stored, and presented to users.

---

## Limitations

- Retrieval quality depends on PDF and OCR quality.
- The current evaluation dataset is relatively small and should be expanded for broader benchmarking.
- Lexical retrieval may miss semantically related passages that use significantly different terminology.
- AI-generated answers should always be verified using the provided source pages.
- Legal-document analysis is intended for information and document understanding and does not constitute legal advice.
- The current deployment architecture may require additional persistent cloud storage/database infrastructure for production-scale use.

---

## Future Enhancements

- Semantic/vector embeddings
- Hybrid lexical + vector retrieval
- Reranking models
- Larger multi-domain evaluation datasets
- Persistent cloud database and object storage
- Advanced legal-document analysis
- Document timeline extraction
- Named-entity extraction
- Multi-document knowledge search
- Administrative analytics dashboards
- Role-based organizational access

---

## Disclaimer

TN Insight AI is an educational document-intelligence project. AI-generated information should be verified against the original source document, particularly for legal, financial, administrative, or other high-stakes decisions.

---

## Author

**Joshik R**

Computer Science Engineering  
Full-Stack Development • Artificial Intelligence • Information Retrieval