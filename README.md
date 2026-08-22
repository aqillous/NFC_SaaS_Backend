# NFC Review SaaS — Backend

FastAPI backend for the NFC-based Google Review management platform.

See `DEPLOYMENT_GUIDE.md` (in the deployment files) for how this is deployed
on Vercel, and the code comments in `app/` for how each module works.

## Local development

```bash
pip install -r requirements.txt
cp .env.example .env   # then edit with your local DB credentials
alembic upgrade head
uvicorn app.main:app --reload
```

## Tests

```bash
pytest
```
