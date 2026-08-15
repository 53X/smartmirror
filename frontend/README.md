This is the Smartmirror kiosk + staff app (Next.js App Router).

## Scripts

```bash
cd /mnt/c/Users/PRANAY/smartmirror/frontend
npm install
npm run dev
npm test
npm run lint
```

Copy `.env.example` to `.env.local`. Match `NEXT_PUBLIC_KIOSK_DEVICE_TOKEN` with the gateway token.

Staff email auth needs Supabase URL + anon key. For laptop demos, `NEXT_PUBLIC_AUTH_DEV_BYPASS=true` plus gateway `AUTH_DEV_BYPASS=true`.

Packages: Tailwind CSS, Lucide React, Motion (`motion/react`). Do not add `framer-motion`.
