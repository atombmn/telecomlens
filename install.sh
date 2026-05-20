#!/usr/bin/env bash
set -e
echo "=== TelecomLens — Linux/macOS Setup ==="

# Install poppler
if ! command -v pdftotext &>/dev/null; then
  echo "[1/3] Installing pdftotext (poppler-utils)..."
  if command -v apt-get &>/dev/null; then
    sudo apt-get install -y poppler-utils
  elif command -v brew &>/dev/null; then
    brew install poppler
  elif command -v dnf &>/dev/null; then
    sudo dnf install -y poppler-utils
  else
    echo "Please install poppler-utils manually."
    exit 1
  fi
else
  echo "[1/3] pdftotext already installed."
fi

# Python venv
if [ ! -d venv ]; then
  echo "[2/3] Creating Python virtual environment..."
  python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt --quiet

# .env
if [ ! -f .env ]; then
  echo "[3/3] Creating .env config..."
  cat > .env << 'EOF'
DATABASE_URL=sqlite:///./telecomlens.db
BILLS_FOLDER=bills
POPPLER_PATH=poppler
EOF
else
  echo "[3/3] .env already exists — skipping."
fi

echo ""
echo "=== Setup complete! Run ./start.sh to launch ==="
