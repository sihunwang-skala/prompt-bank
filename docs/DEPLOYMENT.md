# Deployment (not performed)
No deployment was done (no credentials/hosting). Suggested low-cost path:
1. API: any container host. `pip install -r services/api/requirements.txt`; run `uvicorn app.main:app --host 0.0.0.0 --port 8000`. Set env vars from `.env.example`. Use `RAW_DATABASE_URL` for Postgres (add `psycopg`; **untested**) and a persistent volume for `RAW_DATA_DIR`. Run a single instance (jobs run in-process; multiple instances would need a shared queue).
2. Web: `npm install && npm run build:web`, host on any Node host/Vercel with `NEXT_PUBLIC_API_URL`. Restrict CORS in `app/main.py` to your web origin (currently localhost only).
3. Mobile: `cd apps/mobile && npx expo start` / EAS build. **The scaffold has never been built.**
4. Before real use: add HTTPS, token expiry, Alembic migrations, a shared rate limiter, and retention enforcement.
