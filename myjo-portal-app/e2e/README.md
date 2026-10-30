# Browser tests (Playwright)

Run against a freshly seeded database with the API and the built front end running:

```bash
cd backend && flask --app wsgi init-db --drop && flask --app wsgi seed
gunicorn --bind 127.0.0.1:5000 wsgi:app &          # API
cd ../frontend && npm run build && npx vite preview --port 4173 &   # app + /api proxy
pip install playwright && python -m playwright install chromium
mkdir -p e2e/out
python e2e/smoke.py http://localhost:4173 e2e/out   # every role, every screen, desktop + phone
python e2e/flow.py  http://localhost:4173           # distributor order -> school portal -> academic team
python e2e/review_flow.py http://localhost:4173     # menu badges; distributor in review mode adds a new school + order
```

`smoke.py` must run first: it completes the first-time password/PIN setup (password `Smoke2026x`, PIN `4826`) that `flow.py` and `review_flow.py` sign in with. Reseed before running the set again.
