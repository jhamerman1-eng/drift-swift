#!/usr/bin/env bash
set -euo pipefail

# Usage: ./scripts/init_repo.sh [main-branch] [remote-url]

DEFAULT_BRANCH=${1:-main}
REMOTE_URL=${2:-}

git init -b "$DEFAULT_BRANCH"
git add .
git commit -m "chore: initial commit – Sprint 0 core infra (client + orchestrator)"

git branch -M "$DEFAULT_BRANCH"
git checkout -b dev
if [[ -n "$REMOTE_URL" ]]; then
  git remote add origin "$REMOTE_URL" || true
  git push -u origin dev || true
  git checkout "$DEFAULT_BRANCH"
  git push -u origin "$DEFAULT_BRANCH" || true
fi

# Install pre-commit hooks if available
if command -v pre-commit >/dev/null 2>&1; then
  pre-commit install
fi

echo "✅ Repo initialized. Branches: $DEFAULT_BRANCH and dev"
