#!/usr/bin/env bash
set -e
source venv/bin/activate 2>/dev/null || { echo "Run ./install.sh first"; exit 1; }

echo ""
echo "  ============================================================"
echo "  TelecomLens  |  http://localhost:8000"
echo "  Click Stop in the browser, or press Ctrl+C to quit."
echo "  ============================================================"
echo ""

(sleep 1.5 && (open http://localhost:8000 2>/dev/null || xdg-open http://localhost:8000 2>/dev/null || true)) &

python -m uvicorn main:app --port 8000

echo ""
echo "  TelecomLens has stopped."
