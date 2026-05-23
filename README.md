# Slidelang

A deck-as-code authoring platform. Natural-language prompts → typed JSON deck specs → reveal.js HTML slides.

## Architecture

```
[prompt] → [Claude] → [JSON DSL] → [validate/repair] → [compile] → [reveal.js HTML]
```

See [`CLAUDE.md`](./CLAUDE.md) for engineering invariants and [`docs/TDD.md`](./docs/TDD.md) for the technical design.

## Quickstart

### Backend

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"
cp .env.example .env  # add your ANTHROPIC_API_KEY
python -m app.schema.export_schema
pytest
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Open http://localhost:3000.

## Deploy

- Backend: Railway (root directory: `backend`)
- Frontend: Vercel (root directory: `frontend`)

## License

MIT
