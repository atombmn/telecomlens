#!/usr/bin/env bash
source venv/bin/activate 2>/dev/null || true
echo "Starting TelecomLens on http://localhost:8000 ..."
(sleep 1.5 && open http://localhost:8000 2>/dev/null || xdg-open http://localhost:8000 2>/dev/null) &
python -m uvicorn main:app --port 8000 --reload
