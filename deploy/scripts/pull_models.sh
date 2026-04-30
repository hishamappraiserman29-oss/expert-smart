#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────
# Ollama init script:
#   1. starts ollama serve in background
#   2. pulls $OLLAMA_MODEL (default: llama3:8b)
#   3. creates the $ALIAS_AS tag (default: qwen2.5:7b) so existing
#      core_engine code finds the same model name unchanged
#   4. brings ollama serve to the foreground (so the container stays alive)
# ─────────────────────────────────────────────────────────────────────────
set -e

MODEL="${OLLAMA_MODEL:-llama3:8b}"
ALIAS="${ALIAS_AS:-qwen2.5:7b}"

echo "=========================================================="
echo " Ollama init"
echo "  model:    ${MODEL}"
echo "  alias:    ${ALIAS}  (created so core_engine works unmodified)"
echo "=========================================================="

# Start the daemon in the background
ollama serve &
OLLAMA_PID=$!

# Wait until /api/tags responds
echo "[ollama-init] waiting for daemon..."
for i in $(seq 1 60); do
  if ollama list >/dev/null 2>&1; then
    echo "[ollama-init] daemon is up"
    break
  fi
  sleep 2
done

# Pull the real model (idempotent; skips if already cached)
echo "[ollama-init] pulling ${MODEL} (this may take a few minutes on first run)..."
ollama pull "${MODEL}"

# Create the alias the existing code references
# `ollama cp` works as a tag alias — both names point at the same weights.
if [ "${MODEL}" != "${ALIAS}" ]; then
  echo "[ollama-init] creating alias ${ALIAS} → ${MODEL}"
  ollama cp "${MODEL}" "${ALIAS}" || echo "[ollama-init] alias already exists, skipping"
fi

echo "[ollama-init] ready. ${ALIAS} alias is now serving ${MODEL}."

# Forward signals to the daemon and wait
trap "kill -TERM ${OLLAMA_PID}" TERM INT
wait ${OLLAMA_PID}
