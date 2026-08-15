# Smartmirror

In-store **sari try-on kiosk**: reconstruct a sari from part photos (Stage A), then generate a photoreal **still** on the customer (Stage B). Generated stills are “how it would look.” The cloth in hand is the source of truth.

Live AR overlay is out of scope.

## Folder map

```
frontend/                          Next.js App Router (kiosk + staff)
backend/shared/                   Part types and shared Pydantic models
backend/services/gateway/         FastAPI BFF (auth + proxy)
backend/services/catalog/         SKUs, parts, approve flag
backend/services/ai_service/      Stage A reconstruct + Stage B try-on jobs
docs/capture-sop.md                Staff part-shot protocol
docs/architecture.md               System sketch
```

## Local run (WSL)

Project root: `/mnt/c/Users/PRANAY/smartmirror`

1. Copy `.env.example` to `.env`. For the UI, also copy `frontend/.env.example` to `frontend/.env.local`.
2. Use matching `KIOSK_DEVICE_TOKEN` in gateway and `NEXT_PUBLIC_KIOSK_DEVICE_TOKEN`.
3. For staff auth without a live Supabase project, set `AUTH_DEV_BYPASS=true` and `NEXT_PUBLIC_AUTH_DEV_BYPASS=true` (local only).

### Backend (three venvs)

```bash
cd /mnt/c/Users/PRANAY/smartmirror/backend/services/catalog
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=../../shared:. uvicorn app.main:app --host 0.0.0.0 --port 8002

cd /mnt/c/Users/PRANAY/smartmirror/backend/services/ai_service
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=../../shared:. uvicorn app.main:app --host 0.0.0.0 --port 8003

cd /mnt/c/Users/PRANAY/smartmirror/backend/services/gateway
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=../../shared:. uvicorn app.main:app --host 0.0.0.0 --port 8001
```

### Frontend

```bash
cd /mnt/c/Users/PRANAY/smartmirror/frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Kiosk: `/kiosk/consent`. Staff: `/staff/login`.

### Tests

```bash
cd /mnt/c/Users/PRANAY/smartmirror/backend/services/catalog && source venv/bin/activate
PYTHONPATH=../../shared:. pytest

cd /mnt/c/Users/PRANAY/smartmirror/backend/services/ai_service && source venv/bin/activate
PYTHONPATH=../../shared:. pytest

cd /mnt/c/Users/PRANAY/smartmirror/frontend && npm test
```

## What is real vs stubbed

| Piece | Status |
| --- | --- |
| Catalog SKUs | Real Wikimedia sari photos for demo; staff capture for live SKUs |
| Stage A | Uses `full_hanging` as the garment. No labeled collage as try-on input |
| Stage B | **OpenAI gpt-image-1** or **FASHN v1.6** drapes the sari on the customer still. Overlay stub is off |
| Staff auth | Supabase when configured; local bypass for laptop |
| Live overlay | Not built |

See `docs/capture-sop.md` (five shots) and `docs/sari-datasets.md`.

## Hosted demo (Vercel + Railway)

- **Frontend:** Vercel project `smartmirror` (root `frontend/`). Observability Plus is off.
- **Backend:** Railway project `smartmirror` — services `catalog`, `ai-service`, `gateway`. Only `gateway` is public.
- Set `NEXT_PUBLIC_GATEWAY_URL` on Vercel to the gateway `*.up.railway.app` URL (no trailing slash).
- Match `KIOSK_DEVICE_TOKEN` (Railway gateway) with `NEXT_PUBLIC_KIOSK_DEVICE_TOKEN` (Vercel).
- Put `OPENAI_API_KEY` on the Railway `ai-service` only. Never commit it.

