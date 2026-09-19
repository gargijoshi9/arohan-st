# arohan-st

## Project Structure

```
arohan-st/
├── backend/          # Backend API (Python/FastAPI)
│   ├── data/         # Data files and scheme configs
│   ├── models/       # Database models
│   ├── routers/      # API routes
│   ├── schemas/      # Pydantic schemas
│   ├── services/     # Business logic
│   └── utils/        # Utility functions
├── frontend/         # Frontend (React/TypeScript)
│   └── src/
│       ├── api/      # API clients
│       ├── components/  # Reusable components
│       ├── hooks/    # Custom hooks
│       └── pages/    # Page components
└── docs/             # Documentation
```

## Setup

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your configuration
uvicorn main:app --reload
```

### Frontend
```bash
cd frontend
npm install
cp .env.example .env
# Edit .env with your configuration
npm run dev
```

## Environment Variables

See `.env.example` for required variables.

## License

MIT