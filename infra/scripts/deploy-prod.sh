#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BRANCH="${DEPLOY_BRANCH:-main}"
REMOTE="${DEPLOY_REMOTE:-origin}"
ENV_FILE="${DEPLOY_ENV_FILE:-$ROOT_DIR/.env.prod}"
COMPOSE_FILE="${DEPLOY_COMPOSE_FILE:-$ROOT_DIR/infra/compose/docker-compose.prod.yml}"
LOCK_FILE="${DEPLOY_LOCK_FILE:-/tmp/async-docflow-deploy.lock}"
TARGET_SHA="${1:-}"

log() {
  printf '[deploy] %s\n' "$1"
}

fail() {
  printf '[deploy] ERROR: %s\n' "$1" >&2
  exit 1
}

detect_docker_cmd() {
  if docker info >/dev/null 2>&1; then
    DOCKER_CMD=(docker)
    return
  fi

  if command -v sudo >/dev/null 2>&1 && sudo docker info >/dev/null 2>&1; then
    DOCKER_CMD=(sudo docker)
    return
  fi

  fail "docker daemon is not reachable by current user"
}

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  fail "another deployment is already running (lock: $LOCK_FILE)"
fi

cd "$ROOT_DIR"
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || fail "not a git repository: $ROOT_DIR"

log "syncing branch '$BRANCH' from remote '$REMOTE'"
git fetch "$REMOTE" "$BRANCH"

current_branch="$(git rev-parse --abbrev-ref HEAD)"
if [ "$current_branch" != "$BRANCH" ]; then
  log "checking out branch '$BRANCH'"
  git checkout "$BRANCH"
fi

git pull --ff-only "$REMOTE" "$BRANCH"

if [ -n "$TARGET_SHA" ]; then
  if git merge-base --is-ancestor "$TARGET_SHA" HEAD; then
    log "verified pushed commit is included in deployed HEAD ($TARGET_SHA)"
  else
    fail "deployed HEAD does not contain pushed commit: $TARGET_SHA"
  fi
fi

[ -f "$ENV_FILE" ] || fail "env file not found: $ENV_FILE"
[ -f "$COMPOSE_FILE" ] || fail "compose file not found: $COMPOSE_FILE"

log "running production preflight checks"
bash "$ROOT_DIR/infra/scripts/preflight-prod.sh" "$COMPOSE_FILE" "$ENV_FILE"

DOCKER_CMD=()
detect_docker_cmd
log "rebuilding and restarting compose services"
"${DOCKER_CMD[@]}" compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --build --remove-orphans

log "deployment finished at commit $(git rev-parse --short HEAD)"
