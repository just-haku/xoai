#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="$SCRIPT_DIR/.venv"
VENV_PYTHON="$VENV_DIR/bin/python"

ensure_local_venv() {
    if [ ! -x "$VENV_PYTHON" ]; then
        echo "🐍 Creating project virtualenv at $VENV_DIR"
        python3 -m venv "$VENV_DIR"
        "$VENV_PYTHON" -m pip install --upgrade pip
        "$VENV_PYTHON" -m pip install -e ./backend
    fi
}

# Load .env if exists
if [ -f .env ]; then
    set -a; source .env; set +a
fi

case "${1:-up}" in
    up)
        echo "🥭 Starting XOAI..."
        docker compose up --build -d
        echo "✅ XOAI is running."
        echo "   Backend:  http://localhost:8080"
        echo "   Frontend: http://localhost:3080"
        ;;
    down)
        echo "🛑 Stopping XOAI..."
        docker compose down
        echo "✅ XOAI stopped."
        ;;
    logs)
        docker compose logs -f "${2:-}"
        ;;
    restart)
        docker compose restart "${2:-}"
        ;;
    shell)
        docker exec -it xoai-backend bash
        ;;
    venv)
        ensure_local_venv
        echo "✅ Virtualenv ready at $VENV_DIR"
        echo "   Activate with: source .venv/bin/activate"
        ;;
    backend)
        ensure_local_venv
        exec "$VENV_PYTHON" -m xoai.cli start --port "${2:-8080}" --host "${3:-0.0.0.0}"
        ;;
    drop-db)
        echo "⚠️  Dropping XOAI database..."
        ensure_local_venv
        "$VENV_PYTHON" scripts/drop_db.py
        ;;
    rebuild)
        echo "🔄 Rebuilding XOAI without cache..."
        docker compose build --no-cache
        docker compose up -d
        echo "✅ XOAI rebuilt and running."
        ;;
    add)
        if [ "${2:-}" == "admin" ]; then
            ensure_local_venv
            "$VENV_PYTHON" scripts/manage_users.py add admin "${3:-}" "${4:-}" "${5:-}"
        else
            echo "Usage: ./run_xoai.sh add admin <user> <pwd> <name>"
        fi
        ;;
    *)
        echo "Usage: ./run_xoai.sh [up|down|logs|restart|shell|venv|backend|drop-db|rebuild|add admin]"
        exit 1
        ;;
esac
