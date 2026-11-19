# ADIP Frontend

React + TypeScript + Vite + Tailwind. Screens are listed in the root README, section 24.

## Run

```bash
npm install
npm run dev        # http://localhost:5173 (uses mock data by default)
npm run test       # Vitest
npm run build      # typecheck + production build
```

## How it fits together

- `../../packages/shared-schemas/*.json` is the contract shared with the backend.
- `npm run gen:types` regenerates `src/types/generated/` from those schemas. Never edit those files by hand.
- `src/types/requirements.zod.ts` adds runtime validation (including the cross-field rules from `ml/src/requirements/schemas.py`).
- `src/mocks/` (MSW) fakes `/api/v1/*` until FastAPI routes exist. Mock values are invented for UI work, not model output. Set `VITE_USE_MOCKS=false` to use the real API (proxied to `localhost:8000`).
- `src/routes.tsx` lists the 12 screens; add new screens there.
- `src/features/<name>/` holds data hooks; `src/pages/` holds screens.
