# CogniGraph React UI migration package

This is a **frontend + API adapter patch** designed to be added to your existing working CogniGraph project. It does not replace your existing `app/`, `llm/`, `rag/`, `router/`, `storage.py`, `config.py`, `.venv`, `data/`, ChromaDB, uploaded course PDFs, or trained adapter.

## What is included

- `frontend/`: React + TypeScript + Vite UI with login/register, overview dashboard, Socratic tutor, source citations, Explain/Visualize actions, quiz with progressive hints, revision mode, weak topics, course creation, PDF upload, chat history, saved visuals, and progress dashboard.
- `api_main.py`: FastAPI routes that call the existing CogniGraph modules.
- `requirements-api.txt`: the small set of additional API dependencies.

## Install into your existing project (Windows PowerShell)

1. Extract this ZIP somewhere temporary, for example `D:\Aman project\CogniGraph_React_UI_Migration`.
2. Copy the extracted `frontend` folder into your existing project root:
   `D:\Aman project\CogniGraph_v2_Phase5_Workspace\frontend`
3. Copy `api_main.py` and `requirements-api.txt` into the **root** of your existing project, beside `storage.py`, `config.py`, and `llm/`.
4. Open PowerShell in the existing project root and activate your existing `.venv`:
   ```powershell
   cd "D:\Aman project\CogniGraph_v2_Phase5_Workspace"
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements-api.txt
   ```
5. Terminal 1 — start API from the project root:
   ```powershell
   python -m uvicorn api_main:app --reload --host 127.0.0.1 --port 8000
   ```
   Verify `http://127.0.0.1:8000/health` and open API docs at `http://127.0.0.1:8000/docs`.
6. Terminal 2 — start React UI:
   ```powershell
   cd "D:\Aman project\CogniGraph_v2_Phase5_Workspace\frontend"
   npm install
   npm run dev
   ```
   Open `http://localhost:5173`.

The frontend uses `http://127.0.0.1:8000` by default. If needed, create `frontend/.env.local` with:
`VITE_API_URL=http://127.0.0.1:8000`

## Keep these safeguards

- Do not delete or overwrite your `.venv`, `data/`, `config.py`, `storage.py`, model adapter, or ChromaDB.
- First test login, course selection, upload a PDF, ask a tutor question, generate a quiz, and use Explain/Visualize.
- The first model-backed request can still be slow because the existing model runs on the backend machine. React does not accelerate inference. Hosted inference is the next phase.
- The API uses an in-memory token map for local single-process development. Before production, replace it with persistent secure sessions/JWT, configure HTTPS and exact CORS origins, and use durable storage. Do not expose this development configuration directly to the public internet.
- Mermaid diagrams render in the frontend. Chart/concept-map images are rendered from backend-generated PNGs. Saved visuals are stored in the existing CogniGraph database.

## Important implementation note

This is an end-to-end UI and API integration starter built against the supplied project code. It should be tested against your actual local dependencies and adapter before you treat it as production-ready. The current adapter uses the same `SocraticEngine`, retrieval, router, learning module, and storage layer as the existing Streamlit app; it does not retrain or replace your LLM.
