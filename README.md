# CogniGraph — Socratic AI Learning Platform

CogniGraph is an AI-powered learning platform designed to help students study from their own course materials. Students can create courses, upload lecture PDFs, ask questions, receive guided explanations, inspect source references, practise with quizzes, review weak topics, and view learning progress.

The project uses a **React + TypeScript frontend** and a **Python FastAPI backend**. The backend connects the user interface to CogniGraph's existing document-ingestion, retrieval-augmented generation (RAG), Socratic tutoring, learning, visualization, and storage modules.

> **Project note:** The React interface and FastAPI API are an integration layer around the existing CogniGraph modules. They do not replace the existing `llm/`, `rag/`, `router/`, `app/`, `storage.py`, `config.py`, ChromaDB data, course uploads, or trained adapter.

## Main capabilities

- **Course management:** Create and select courses.
- **PDF ingestion:** Upload course PDFs, extract text, split it into chunks, and preserve source/page metadata.
- **Course-grounded tutoring:** Ask questions and retrieve relevant passages from the selected course.
- **Socratic learning:** Guide learning with prompts, hints, explanations, and follow-up questions rather than relying only on direct answers.
- **Source references:** Return source information so students can inspect the supporting course material.
- **Explain and visualize actions:** Request explanations, charts, diagrams, or concept maps.
- **Quizzes:** Generate questions, submit answers, and receive feedback.
- **Revision and weak topics:** Generate revision material and identify topics that may need more practice.
- **Study planning and progress:** Create study plans and view course-level learning progress.
- **Conversation and saved-visual history:** Revisit conversations and saved visual outputs.

## Architecture

```text
React + TypeScript + Vite
          |
          | HTTP / REST requests
          v
     FastAPI API
       api_main.py
          |
          +---- Authentication and course workflows
          |
          +---- PDF ingestion
          |       ingestion/pdf_processor.py
          |
          +---- RAG retrieval
          |       rag/retriever.py
          |       rag/vectorstore.py
          |       BGE-M3 embeddings + ChromaDB
          |
          +---- Socratic tutoring and LLM integration
          |       llm/socratic_engine.py
          |       llm/base.py and model backends
          |
          +---- Learning services
          |       learning.py
          |       study_schedule.py
          |
          +---- Multimodal routing and visualization
          |       router/
          |       orchestration/
          |       visualization/
          |
          +---- Structured application storage
                  storage.py + SQLite
```

### Main technologies

| Layer | Technologies |
|---|---|
| Frontend | React, TypeScript, Vite |
| Backend API | Python, FastAPI, Uvicorn |
| Document processing | PyPDF (`pypdf`) |
| Embeddings | BGE-M3 (`BAAI/bge-m3`) |
| RAG / vector storage | LangChain, ChromaDB |
| Language models | Fine-tuned Llama adapter integration and optional hosted-model integrations |
| Model adaptation | PEFT / LoRA |
| Structured data | SQLite |
| Charts and concept maps | Matplotlib, NetworkX |
| Diagrams | Mermaid |

## Repository structure

```text
CogniGraph/
├── frontend/                 # React + TypeScript + Vite application
├── api_main.py               # FastAPI application and API endpoints
├── app/                      # Existing Streamlit interface
├── auth.py                   # Authentication helpers for the Streamlit interface
├── config.py                 # Application, RAG, ingestion, and LLM configuration
├── storage.py                # SQLite connection and database operations
├── learning.py               # Quiz, revision, and explanation logic
├── study_schedule.py         # Study-plan generation
├── ingestion/                # PDF extraction and chunking
├── rag/                      # Vector-store and retrieval logic
├── llm/                      # Socratic engine and LLM integrations
├── router/                   # Output-mode routing
├── orchestration/            # Visualization workflow coordination
├── visualization/            # Charts, diagrams, and concept maps
├── tests/                    # Automated tests
├── scripts/                  # Evaluation and utility scripts
├── adapter/                  # Fine-tuned model adapter artifacts
├── Cognigraphi Dataset/      # Socratic training / evaluation datasets
├── data/                     # Runtime data (created/used locally; not committed)
├── requirements.txt          # Core project dependencies
├── requirements-api.txt      # FastAPI/API dependencies
├── start_api.ps1             # Windows PowerShell API starter
└── start_frontend.ps1        # Windows PowerShell frontend starter
```

## Requirements

Install the following on the development machine:

- Python and `pip`
- Node.js and `npm`
- Git
- Git LFS (needed to download the model adapter file tracked with Git LFS)

The full Python requirements include machine-learning and embedding dependencies. Installing them can take time and may require significant disk space. Model inference speed depends on the backend machine and its available CPU/GPU resources.

## Get the project

Clone the repository and download Git LFS objects:

```powershell
git clone https://github.com/ikrammir12/CogniGraph-.git
cd CogniGraph-
git lfs install
git lfs pull
```

If the repository has already been cloned, run `git lfs pull` from the project root to download the adapter weights.

## Local setup — Windows PowerShell

Run the backend and frontend in **two separate PowerShell terminals**.

### 1. Prepare the Python environment

From the project root:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-api.txt
```

If PowerShell blocks virtual-environment activation, use the appropriate execution-policy setting for your machine or activate the environment using another supported shell. Do not delete an existing working `.venv`; reuse it when it already contains the project's dependencies.

### 2. Configure the frontend API URL

Create `frontend/.env.local` with:

```env
VITE_API_URL=http://127.0.0.1:8000
```

The frontend reads this value to send API requests to the local FastAPI server. Keep local environment files and secrets out of Git.

### 3. Start the backend — Terminal 1

From the project root, with the Python environment activated:

```powershell
python -m uvicorn api_main:app --reload --host 127.0.0.1 --port 8000
```

Verify the API health endpoint:

- Health: <http://127.0.0.1:8000/api/health>
- Interactive API documentation: <http://127.0.0.1:8000/docs>

### 4. Start the frontend — Terminal 2

```powershell
cd frontend
npm install
npm run dev
```

Open the local frontend at <http://localhost:5173>.

`npm install` is needed when setting up the frontend or after its dependency manifest changes. For later runs, start the backend and run `npm run dev` from `frontend/`.

### Optional: build the frontend

From the `frontend/` directory:

```powershell
npm run build
```

The production build is generated in `frontend/dist/`.

## Database and runtime data

CogniGraph uses two different storage systems:

- **SQLite:** Stores structured application records such as users, courses, conversations, messages, quiz attempts, study plans, and progress. Database operations are managed through `storage.py`.
- **ChromaDB:** Stores document chunks, embeddings, and source metadata for semantic retrieval. The vector-store integration is in `rag/vectorstore.py`.

The application uses course identifiers to select course-specific vector collections. SQLite and ChromaDB are separate stores; they do not share relational foreign-key constraints.

Runtime data is kept under `data/` (including SQLite, ChromaDB persistence, uploads, and saved visualizations, depending on the configured paths). Runtime databases and uploaded user files are intentionally excluded from the Git repository. Back them up separately when needed.

## Model configuration

LLM configuration is centralized in `config.py`. The selected backend and model paths can be controlled through environment variables, including:

| Variable | Purpose |
|---|---|
| `COGNIGRAPH_LLM_BACKEND` | Selects the configured LLM backend |
| `COGNIGRAPH_BASE_MODEL` | Base model identifier/path for adapter loading |
| `COGNIGRAPH_MODEL_PATH` | Local adapter/model path |
| `COGNIGRAPH_EMBED_MODEL` | Embedding model identifier |
| `COGNIGRAPH_RAG_THRESHOLD` | Retrieval relevance threshold |

The repository includes a fine-tuned adapter artifact tracked using Git LFS. A local machine must have the correct base model available and `COGNIGRAPH_MODEL_PATH` configured to a valid path. Model loading and inference can be resource-intensive. Optional hosted-model integrations require the relevant provider credentials to be configured securely; never commit API keys or `.env` files.

## API overview

The FastAPI application is defined in `api_main.py`. Main route groups include:

| Route | Purpose |
|---|---|
| `POST /api/auth/register` | Register a user |
| `POST /api/auth/login` | Log in |
| `GET /api/courses` / `POST /api/courses` | List and create courses |
| `POST /api/courses/{course_id}/upload` | Upload a course PDF |
| `POST /api/chat` | Send a tutoring question |
| `POST /api/actions/explain` | Request an explanation |
| `POST /api/actions/visualize` | Request a visualization |
| `POST /api/quiz/question` | Generate a quiz question |
| `POST /api/quiz/answer` | Submit a quiz answer |
| `POST /api/revision` | Generate revision material |
| `GET /api/courses/{course_id}/weak-topics` | Retrieve weak-topic information |
| `GET /api/courses/{course_id}/dashboard` | Retrieve course progress data |

For the complete request and response schemas, run the API and open `/docs`.

## Tests and validation

The repository includes tests for areas such as ingestion/storage, retrieval, grounding, learning, quizzes, Socratic tutoring, routing, and visualization.

Run the project tests from the root after installing the dependencies:

```powershell
python -m pytest
```

Some tests or workflows may depend on local model files, runtime data, external model services, or environment configuration. Confirm those prerequisites before interpreting a test failure as a code defect.

## Known limitations and security notes

- The React frontend does not make model inference faster; response time depends on the configured model backend and hardware or hosted service.
- The current API uses an in-memory token/session map for local single-process development. It is not suitable as-is for a public production deployment. Use persistent secure sessions or JWT-based authentication before production.
- Configure HTTPS, restrictive CORS origins, secret management, access controls, rate limits, and durable storage before exposing the API publicly.
- Mermaid diagrams render in the frontend. Chart and concept-map images are generated by backend visualization modules.
- The image-generation module is a placeholder and does not currently provide a connected image-generation service.
- Fine-tuning artifacts in the repository do not, by themselves, establish that a training run has been fully evaluated. Report training metrics only when supported by verified experiment records.
- This repository is an academic project and should be tested and security-reviewed before production use.

## Contributing / development workflow

1. Create a feature branch for a change.
2. Keep frontend, API, retrieval, and storage responsibilities separated.
3. Add or update tests for changed behaviour.
4. Do not commit `.venv/`, `node_modules/`, `.env` files, runtime databases, uploaded private PDFs, or ChromaDB persistence files.
5. Use Git LFS for large model artifacts tracked by the repository.

