#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────
# Flask container entrypoint
# ─────────────────────────────────────────────────────────────────────────
set -e

echo "==============================================="
echo "  Expert_Smart Flask container starting"
echo "==============================================="
echo "  OLLAMA_HOST  = ${OLLAMA_HOST}"
echo "  QDRANT_URL   = ${QDRANT_URL:-http://qdrant:6333}"
echo "  PORT         = ${PORT:-5000}"
echo "  PYTHONPATH   = ${PYTHONPATH}"
echo "==============================================="

# Wait for Ollama to be reachable (max 120s)
if [ -n "${OLLAMA_HOST}" ]; then
  echo "[entrypoint] waiting for Ollama at ${OLLAMA_HOST}..."
  for i in $(seq 1 24); do
    if curl -fsS "${OLLAMA_HOST}/api/tags" >/dev/null 2>&1; then
      echo "[entrypoint] Ollama is ready"
      break
    fi
    sleep 5
  done
fi

# Allow override of WSGI server via $WSGI (default: waitress; production: gunicorn)
WSGI="${WSGI:-waitress}"

cd /app

if [ "$WSGI" = "gunicorn" ]; then
  echo "[entrypoint] launching gunicorn..."
  exec gunicorn \
       -k gthread \
       -w "${GUNICORN_WORKERS:-4}" \
       --threads "${GUNICORN_THREADS:-8}" \
       --timeout "${GUNICORN_TIMEOUT:-180}" \
       --bind "0.0.0.0:${PORT:-5000}" \
       --access-logfile - \
       --error-logfile - \
       core_engine.bridge_api:app
else
  echo "[entrypoint] launching waitress (default)..."
  exec python -m core_engine.bridge_api
fi
