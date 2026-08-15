# AI service

Stage A compose/blend reconstruct and Stage B vendor-agnostic try-on jobs.

```bash
cd /mnt/c/Users/PRANAY/smartmirror/backend/services/ai_service
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=../../shared:. uvicorn app.main:app --reload --port 8003
```

Leave `TRYON_VENDOR_URL` empty to use the stub compositor. When a hosted vendor is chosen, set URL + API key only in env.
