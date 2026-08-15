# Gateway

BFF for kiosk and staff. Verifies Supabase JWT (staff) or device token (kiosk) and forwards to catalog / AI.

```bash
cd /mnt/c/Users/PRANAY/smartmirror/backend/services/gateway
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=../../shared:. uvicorn app.main:app --reload --port 8001
```

Set `AUTH_DEV_BYPASS=true` only on a trusted local machine. Production kiosk must use a rotated `KIOSK_DEVICE_TOKEN`.
