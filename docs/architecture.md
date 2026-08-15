# Smartmirror architecture (Phase 0)

Stills-only in-store kiosk. No live AR overlay, no MediaPipe drape, no WebGL fabric.

```
Staff tablet ──┐
Kiosk display ─┼── Next.js (frontend/) ── FastAPI gateway ─┬── catalog
               │                                           └── ai_service
               └── Supabase Auth (staff only)
```

| Surface | Role |
| --- | --- |
| `frontend/` | Kiosk (consent → still → swipe SKUs) and staff (sign-in, guided capture, approve) |
| `backend/services/gateway` | BFF. Supabase JWT for staff. Device token for kiosk. Forwards to catalog and AI. |
| `backend/services/catalog` | SKUs, part types, reconstructed asset, approve flag, local/object media |
| `backend/services/ai_service` | Stage A compose/blend. Stage B vendor-agnostic try-on (stub or HTTP vendor) |

Shoppers do not create accounts. The kiosk is a store device.

## Stage A vs Stage B

- **Stage A** builds a canonical sari from part photos. Pallu and borders are identity regions.
- **Stage B** puts that sari on one front-facing customer still via a hosted try-on API (stubbed until vendor bake-off).

Do not ship IDM-VTON / CatVTON as the product backend.

## Privacy

- Consent before camera.
- No default face retention. Session timeout (default 10 minutes) clears the still from the browser.
- Services log job IDs and SKU IDs, not face image bytes.
