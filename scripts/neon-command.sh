#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$PROJECT_DIR/backend/venv/bin"
LOG_DIR="$PROJECT_DIR/logs"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"
BACKEND_PID_FILE="$LOG_DIR/backend.pid"
FRONTEND_PID_FILE="$LOG_DIR/frontend.pid"

mkdir -p "$LOG_DIR"

status() {
    local running=0
    if [ -f "$BACKEND_PID_FILE" ] && kill -0 "$(cat "$BACKEND_PID_FILE")" 2>/dev/null; then
        echo "  Backend:  RUNNING (pid $(cat "$BACKEND_PID_FILE")) — http://0.0.0.0:8000"
        running=$((running + 1))
    else
        echo "  Backend:  STOPPED"
    fi
    if [ -f "$FRONTEND_PID_FILE" ] && kill -0 "$(cat "$FRONTEND_PID_FILE")" 2>/dev/null; then
        echo "  Frontend: RUNNING (pid $(cat "$FRONTEND_PID_FILE")) — http://0.0.0.0:3900"
        running=$((running + 1))
    else
        echo "  Frontend: STOPPED"
    fi
    return $((2 - running))
}

start() {
    echo "Starting NEON COMMAND..."

    if [ -f "$BACKEND_PID_FILE" ] && kill -0 "$(cat "$BACKEND_PID_FILE")" 2>/dev/null; then
        echo "  Backend already running (pid $(cat "$BACKEND_PID_FILE"))"
    else
        cd "$PROJECT_DIR/backend"
        nohup "$VENV/uvicorn" main:app --host 0.0.0.0 --port 8000 \
            >> "$BACKEND_LOG" 2>&1 &
        echo $! > "$BACKEND_PID_FILE"
        echo "  Backend started (pid $!) — log: $BACKEND_LOG"
    fi

    if [ -f "$FRONTEND_PID_FILE" ] && kill -0 "$(cat "$FRONTEND_PID_FILE")" 2>/dev/null; then
        echo "  Frontend already running (pid $(cat "$FRONTEND_PID_FILE"))"
    else
        cd "$PROJECT_DIR/frontend"
        nohup npx vite >> "$FRONTEND_LOG" 2>&1 &
        echo $! > "$FRONTEND_PID_FILE"
        echo "  Frontend started (pid $!) — log: $FRONTEND_LOG"
    fi

    sleep 1
    echo ""
    echo "NEON COMMAND is running:"
    echo "  Backend:  http://192.168.68.59:8000"
    echo "  Frontend: http://192.168.68.59:3900"
    echo "  External: https://peace-keeper.app"
    echo ""
    echo "Logs: $LOG_DIR/"
}

stop() {
    echo "Stopping NEON COMMAND..."

    if [ -f "$BACKEND_PID_FILE" ]; then
        local pid
        pid=$(cat "$BACKEND_PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null
            echo "  Backend stopped (pid $pid)"
        else
            echo "  Backend was not running"
        fi
        rm -f "$BACKEND_PID_FILE"
    else
        echo "  Backend: no pid file"
        pkill -f "uvicorn main:app.*8000" 2>/dev/null && echo "  Killed stale backend" || true
    fi

    if [ -f "$FRONTEND_PID_FILE" ]; then
        local pid
        pid=$(cat "$FRONTEND_PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null
            echo "  Frontend stopped (pid $pid)"
        else
            echo "  Frontend was not running"
        fi
        rm -f "$FRONTEND_PID_FILE"
    else
        echo "  Frontend: no pid file"
        pkill -f "vite.*3900" 2>/dev/null && echo "  Killed stale frontend" || true
    fi
}

restart() {
    stop
    sleep 1
    start
}

logs() {
    local which="${1:-all}"
    if [ "$which" = "backend" ] || [ "$which" = "all" ]; then
        echo "=== Backend log (last 30 lines) ==="
        tail -30 "$BACKEND_LOG" 2>/dev/null || echo "  (no log yet)"
    fi
    if [ "$which" = "frontend" ] || [ "$which" = "all" ]; then
        echo "=== Frontend log (last 30 lines) ==="
        tail -30 "$FRONTEND_LOG" 2>/dev/null || echo "  (no log yet)"
    fi
}

case "${1:-}" in
    start)   start ;;
    stop)    stop ;;
    restart) restart ;;
    status)  status ;;
    logs)    logs "${2:-all}" ;;
    *)
        echo "NEON COMMAND service manager"
        echo ""
        echo "Usage: $0 {start|stop|restart|status|logs [backend|frontend|all]}"
        echo ""
        echo "  start   — Start backend + frontend in background"
        echo "  stop    — Stop both services"
        echo "  restart — Stop then start"
        echo "  status  — Show running state"
        echo "  logs    — Tail recent logs"
        ;;
esac
