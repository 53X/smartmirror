# Catalog service

SKUs, SOP part images, reconstructed canonical assets, and the staff approve-before-kiosk flag.

```bash
cd /mnt/c/Users/PRANAY/smartmirror/backend/services/catalog
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=../../shared:. uvicorn app.main:app --reload --port 8002
```

Local media lives under `backend/data/catalog` (gitignored). When `SUPABASE_URL` and service role are set, Deepak will point this store at Postgres + Storage.
