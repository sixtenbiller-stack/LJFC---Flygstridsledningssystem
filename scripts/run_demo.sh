#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."

echo "=== NEON COMMAND — Starting Demo ==="

echo "[1/2] Installing dependencies..."
test -d backend/venv || python3 -m venv backend/venv
backend/venv/bin/pip install -q -r backend/requirements.txt
cd frontend && npm install --silent && cd ..

echo "[2/2] Launching services..."
trap 'kill 0' EXIT

cd backend && ../backend/venv/bin/uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

cd frontend && npx vite &
FRONTEND_PID=$!

echo ""
echo "  Backend:  http://192.168.68.59:8000"
echo "  Frontend: http://192.168.68.59:3900"
echo ""
echo "  Press Ctrl+C to stop."
echo ""

wait
