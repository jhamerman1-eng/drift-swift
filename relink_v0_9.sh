#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: bash relink_v0_9.sh <git-remote-url> [remote-name]"
  exit 1
fi

REMOTE_URL="$1"
REMOTE_NAME="${2:-origin}"

if [ ! -d ".git" ]; then
  echo "No git repo here. Run this from your repo root (after apply_patch.sh)."
  exit 1
fi

if git remote get-url "$REMOTE_NAME" >/dev/null 2>&1; then
  echo "🔁 Updating remote '$REMOTE_NAME' to $REMOTE_URL"
  git remote set-url "$REMOTE_NAME" "$REMOTE_URL"
else
  echo "➕ Adding remote '$REMOTE_NAME' = $REMOTE_URL"
  git remote add "$REMOTE_NAME" "$REMOTE_URL"
fi

echo "⬆️  Pushing branch and tags..."
git push "$REMOTE_NAME" release/v0.9 --tags

echo "✅ Done."
