#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

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
    drop-db)
        echo "⚠️  Dropping XOAI database..."
        # Using mongosh (assuming it's on host)
        mongosh xoai --eval "db.dropDatabase()"
        echo "✅ Database dropped."
        ;;
    *)
        echo "Usage: ./run_xoai.sh [up|down|logs|restart|shell]"
        exit 1
        ;;
esac
