#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="$SCRIPT_DIR/.venv"
VENV_PYTHON="$VENV_DIR/bin/python"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
DEFAULT_BACKEND_PORT="${BACKEND_PORT:-8080}"
DEFAULT_FRONTEND_PORT="${FRONTEND_PORT:-3080}"

if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

ensure_local_venv() {
  if [ ! -x "$VENV_PYTHON" ]; then
    echo "Creating virtualenv at $VENV_DIR"
    python3 -m venv "$VENV_DIR"
    "$VENV_PYTHON" -m pip install --upgrade pip
    "$VENV_PYTHON" -m pip install -e ./backend
  fi
}

compose() {
  docker compose -f "$COMPOSE_FILE" "$@"
}

print_help() {
  cat <<'EOF'
XOAI operator entrypoint

Usage:
  ./run_xoai.sh <command> [args]

Core commands:
  help                      Show this help.
  status                    Show docker compose status.
  up                        Build and start the default stack.
  down                      Stop the stack.
  restart [service]         Restart the whole stack or a single service.
  logs [service]            Tail compose logs.
  shell                     Open a shell in xoai-backend.

Local runtime:
  venv                      Create the local Python virtualenv if needed.
  backend [port] [host]     Run the FastAPI backend locally.
  frontend                  Print frontend local-dev guidance.
  build                     Build the frontend bundle.
  test                      Run backend tests and frontend build.

Data and maintenance:
  drop-db                   Drop the XOAI database.
  add admin <user> <pwd> <name>
                            Create an admin user.
  seed                      Seed prompt versions from disk into Mongo.
  migrate-prompts           Alias of seed.
  reindex-vectors           Reserved Titan hook for vector rebuild.
  scheduler-run             Trigger the in-process scheduler loop once.
  gc-run [--dry-run]        Run storage garbage collection.
  health                    Print backend/frontend endpoint guidance.

Docker/Titan services:
  sandbox-up                Start compose with sandbox profile enabled.

Environment:
  BACKEND_PORT              Local backend port, default 8080.
  FRONTEND_PORT             Local frontend port, default 3080.
  COMPOSE_FILE              Compose file path, default docker-compose.yml.

Storage:
  User workspaces:          /app/storage/users/<user_id>/workspace
  Upload scratch:           /app/storage/users/<user_id>/tmp/uploads
  GC transient TTL:         Controlled by XOAI_TRANSIENT_FILE_TTL_DAYS

Sandbox network modes:
  network_disabled          No outbound network.
  network_allowlisted       Only approved provider domains.
  network_full_user_scoped  Full egress with scoped user/admin secrets.

Large uploads:
  Nginx client_max_body_size is configured in frontend/nginx.conf.
  Backend chunked upload endpoints:
    POST   /api/workspace/files/upload/init
    PUT    /api/workspace/files/upload/<id>/chunk/<index>
    POST   /api/workspace/files/upload/<id>/complete
    DELETE /api/workspace/files/upload/<id>

Recovery:
  Startup restores in-progress file operations from .bak files.
  Storage GC skips pinned/in-use artifacts.
  Restarted jobs use startup jitter to avoid synchronized provider spikes.
EOF
}

case "${1:-help}" in
  help|-h|--help)
    print_help
    ;;
  status)
    compose ps
    ;;
  up)
    compose up --build -d
    echo "Backend:  http://localhost:${DEFAULT_BACKEND_PORT}"
    echo "Frontend: http://localhost:${DEFAULT_FRONTEND_PORT}"
    ;;
  sandbox-up)
    compose --profile sandbox up --build -d
    ;;
  down)
    compose down
    ;;
  logs)
    compose logs -f "${2:-}"
    ;;
  restart)
    compose restart "${2:-}"
    ;;
  shell)
    docker exec -it xoai-backend bash
    ;;
  venv)
    ensure_local_venv
    echo "Virtualenv ready at $VENV_DIR"
    ;;
  backend)
    ensure_local_venv
    exec "$VENV_PYTHON" -m xoai.cli start --port "${2:-$DEFAULT_BACKEND_PORT}" --host "${3:-0.0.0.0}"
    ;;
  frontend)
    echo "Run 'cd frontend && npm install && npm run dev -- --host' for local frontend development."
    ;;
  build)
    (cd frontend && npm run build)
    ;;
  test)
    ensure_local_venv
    "$VENV_PYTHON" -m pytest -q backend/tests
    (cd frontend && npm run build)
    ;;
  drop-db)
    ensure_local_venv
    "$VENV_PYTHON" scripts/drop_db.py
    ;;
  add)
    if [ "${2:-}" != "admin" ]; then
      echo "Usage: ./run_xoai.sh add admin <user> <pwd> <name>" >&2
      exit 1
    fi
    ensure_local_venv
    "$VENV_PYTHON" scripts/manage_users.py add admin "${3:-}" "${4:-}" "${5:-}"
    ;;
  seed|migrate-prompts)
    ensure_local_venv
    "$VENV_PYTHON" - <<'PY'
import asyncio
from xoai.db.mongo import connect_to_mongo, close_mongo_connection
from xoai.prompts.service import seed_prompt_versions_from_disk

async def main():
    await connect_to_mongo()
    try:
        created = await seed_prompt_versions_from_disk()
        print(f"Seeded {created} prompt versions")
    finally:
        await close_mongo_connection()

asyncio.run(main())
PY
    ;;
  reindex-vectors)
    echo "Vector reindex hook is reserved for the Titan vector service rollout."
    ;;
  scheduler-run)
    ensure_local_venv
    "$VENV_PYTHON" - <<'PY'
import asyncio
from xoai.db.mongo import connect_to_mongo, close_mongo_connection
from xoai.jobs import process_due_jobs_once

async def main():
    await connect_to_mongo()
    try:
        await process_due_jobs_once()
        print("Processed due jobs once")
    finally:
        await close_mongo_connection()

asyncio.run(main())
PY
    ;;
  gc-run)
    ensure_local_venv
    DRY_RUN="false"
    if [ "${2:-}" = "--dry-run" ]; then
      DRY_RUN="true"
    fi
    "$VENV_PYTHON" - <<PY
import asyncio
from xoai.db.mongo import connect_to_mongo, close_mongo_connection
from xoai.storage_gc import run_storage_gc

async def main():
    await connect_to_mongo()
    try:
        result = await run_storage_gc(dry_run=${DRY_RUN})
        print(result)
    finally:
        await close_mongo_connection()

asyncio.run(main())
PY
    ;;
  health)
    cat <<EOF
Backend health:  http://localhost:${DEFAULT_BACKEND_PORT}/api/health
Backend ready:   http://localhost:${DEFAULT_BACKEND_PORT}/api/ready
Frontend:        http://localhost:${DEFAULT_FRONTEND_PORT}
EOF
    ;;
  *)
    echo "Unknown command: $1" >&2
    print_help
    exit 1
    ;;
esac
