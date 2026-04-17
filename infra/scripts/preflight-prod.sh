#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="${1:-$ROOT_DIR/infra/compose/docker-compose.prod.yml}"
ENV_FILE="${2:-$ROOT_DIR/.env.prod}"
BUILD_CHECK="${3:-}"
RUNTIME_ENV_FILE="$ROOT_DIR/.env.prod"
TEMP_RUNTIME_ENV=0

pass() {
  echo "[PASS] $1"
}

fail() {
  echo "[FAIL] $1"
  exit 1
}

get_env_value() {
  local key="$1"
  grep -E "^${key}=" "$ENV_FILE" | tail -n 1 | cut -d '=' -f2- | tr -d '\r' | xargs
}

command -v docker >/dev/null 2>&1 || fail "docker is required but not installed"
pass "docker command available"

[ -f "$COMPOSE_FILE" ] || fail "compose file not found: $COMPOSE_FILE"
pass "compose file found: $COMPOSE_FILE"

[ -f "$ENV_FILE" ] || fail "env file not found: $ENV_FILE"
pass "env file found: $ENV_FILE"

cleanup() {
  if [ "$TEMP_RUNTIME_ENV" -eq 1 ] && [ -f "$RUNTIME_ENV_FILE" ]; then
    rm -f "$RUNTIME_ENV_FILE"
  fi
}

trap cleanup EXIT

if [ ! -f "$RUNTIME_ENV_FILE" ]; then
  cp "$ENV_FILE" "$RUNTIME_ENV_FILE"
  TEMP_RUNTIME_ENV=1
  pass "created temporary .env.prod for compose validation"
fi

NODE_ENV_VALUE="$(get_env_value NODE_ENV || true)"
[ "$NODE_ENV_VALUE" = "production" ] || fail "NODE_ENV must be production in $ENV_FILE"
pass "NODE_ENV=production"

API_BASE_URL="$(get_env_value NEXT_PUBLIC_API_BASE_URL || true)"
WS_BASE_URL="$(get_env_value NEXT_PUBLIC_WS_BASE_URL || true)"

echo "$API_BASE_URL" | grep -q '^https://' || fail "NEXT_PUBLIC_API_BASE_URL must start with https://"
echo "$WS_BASE_URL" | grep -q '^wss://' || fail "NEXT_PUBLIC_WS_BASE_URL must start with wss://"
pass "public API/WS URLs are https/wss"

if grep -q -- '--reload' "$COMPOSE_FILE"; then
  fail "compose file contains --reload (development-only setting)"
fi

if grep -q 'pnpm dev' "$COMPOSE_FILE"; then
  fail "compose file contains pnpm dev (development-only setting)"
fi
pass "compose file has no dev-mode command flags"

docker compose -f "$COMPOSE_FILE" --env-file "$RUNTIME_ENV_FILE" config >/dev/null
pass "docker compose config resolved successfully"

if [ "$BUILD_CHECK" = "--build-check" ]; then
  docker build \
    --file "$ROOT_DIR/infra/docker/web.prod.Dockerfile" \
    --build-arg NEXT_PUBLIC_API_BASE_URL="$API_BASE_URL" \
    --build-arg NEXT_PUBLIC_WS_BASE_URL="$WS_BASE_URL" \
    --tag docflow-web-preflight:local \
    "$ROOT_DIR" >/dev/null
  pass "web production image build succeeded"
fi

echo "Production preflight passed. Safe to deploy."