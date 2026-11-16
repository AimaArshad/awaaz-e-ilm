# Awaaz-e-Ilm (آواز علم)

> Voice-controlled audiobook platform for visually impaired students.

## Quick Start

cd frontend : python -m http.server 5173
cd backend: uvicorn app.main:app --reload --port 8000

### With Docker (recommended)

```bash
cp .env.example .env
make dev
# Backend:  http://localhost:8000
# Frontend: http://localhost:5173
# API docs: http://localhost:8000/docs
```

### Local (without Docker)

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

5. Serve the frontend

From the tts-frontend folder:
python -m http.server 5500

Then open http://localhost:5500. Use a server rather than double-clicking the file, because the browser treats file:// pages as a different origin and blocks requests more aggressively.

## Download AI Models

```bash
python scripts/download_models.py
```

## Run Tests

```bash
make test
```

## Keyboard Shortcuts

| Key          | Action           |
| ------------ | ---------------- |
| Space (hold) | Push-to-talk     |
| K            | Play / Pause     |
| J            | Back 30 s        |
| L            | Forward 30 s     |
| N            | Next chapter     |
| P            | Previous chapter |
| ?            | Help             |

## Voice Commands (examples)

- "Go to chapter 5" / "باب پانچ پر جاؤ"
- "Forward thirty seconds" / "30 سیکنڈ آگے"
- "Read in Urdu" / "اردو میں پڑھو"
- "Pause" / "رکو"

## Known Limitations

- Urdu OCR on Nastaliq-style or low-quality scans is error-prone.
- MMS Urdu TTS is intelligible but less natural than English voices.
- Whisper Urdu accuracy is moderate; voice commands use a constrained grammar.

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Model Licenses

See [docs/MODELS_AND_LICENSES.md](docs/MODELS_AND_LICENSES.md).
