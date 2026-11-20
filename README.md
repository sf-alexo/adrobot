# Adrobot — Keitaro Campaign Creator + Editor

FastAPI + SQLAlchemy + React app that creates Keitaro campaigns with two streams and edits offers on existing campaigns.

## Features

1. **Create campaign** — name, geo country code, offer ID, domain, group, traffic source  
   - Stream 1 (`regular`): visitors from the selected country → `https://www.google.com`  
   - Stream 2 (`default`): remaining traffic → selected offer  
2. **Stream editor**:
   - **Fetch streams** — pull streams from Keitaro
   - Streams without offers are listed but not editable
   - Add / Remove / Bring back offers with share recalculation
   - Pin a custom share %; unpinned offers split the rest equally (always totals 100%)
   - Dirty draft → **Push to Keitaro** / **Cancel**

## Setup

### 1. Backend env

```bash
cd backend
cp .env.example .env
# fill KEITARO_BASE_URL and KEITARO_API_KEY
```

### 2. Python deps + DB migrations

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
```

Migrations live in `backend/alembic/versions/`. After model changes:

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

> On first boot the API also runs `create_all` as a safety net, but **prefer Alembic** so schema stays versioned.

### 3. Run API

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — Vite proxies `/api` to the backend.

## Config (`.env`)

```
KEITARO_BASE_URL=https://your-tracker.example
KEITARO_API_KEY=your-api-key
# optional — default is absolute path to backend/adrobot.db
# DATABASE_URL=sqlite+aiosqlite:///./adrobot.db
```

Do **not** commit `.env` (it is gitignored). Use `.env.example` as a template.

## API

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/campaigns` | Create campaign + 2 streams |
| `GET` | `/api/campaigns` | List locally tracked campaigns |
| `GET` | `/api/campaigns/{id}` | Campaign + local streams |
| `POST` | `/api/campaigns/{id}/fetch-streams` | Sync streams from Keitaro |
| `POST` | `/api/campaigns/{id}/streams/{sid}/offers` | Add offer (draft) |
| `POST` | `.../offers/{oid}/remove` | Soft-remove offer |
| `POST` | `.../offers/{oid}/bring-back` | Restore offer |
| `POST` | `.../offers/{oid}/pin` | Pin / unpin share (`{ pinned, share }`) |
| `POST` | `.../streams/{sid}/push` | Publish draft to Keitaro (shares must sum to 100) |
| `POST` | `.../streams/{sid}/cancel` | Discard draft |
| `GET` | `/api/meta/domains` | Domains from Keitaro |
| `GET` | `/api/meta/groups` | Campaign groups |
| `GET` | `/api/meta/traffic-sources` | Traffic sources |
| `GET` | `/api/meta/offers` | Offers |
| `GET` | `/api/meta/offers/{id}` | Lookup offer by ID |

## Stack

- Backend: FastAPI, SQLAlchemy 2 (async), Alembic, httpx → Keitaro Admin API
- Frontend: Vite + React + react-router
- DB: SQLite by default
