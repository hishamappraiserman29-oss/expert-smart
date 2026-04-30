#!/usr/bin/env bash
# Container readiness probe for the Flask service.
# Returns 0 if /api/advisor/health responds with HTTP 200.

PORT="${PORT:-5000}"
URL="http://localhost:${PORT}/api/advisor/health"

if command -v curl >/dev/null 2>&1; then
  curl -fsS "${URL}" >/dev/null && exit 0
elif command -v python >/dev/null 2>&1; then
  python -c "import urllib.request,sys; urllib.request.urlopen('${URL}',timeout=5); sys.exit(0)" && exit 0
fi
exit 1
