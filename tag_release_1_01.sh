#!/usr/bin/env bash
set -euo pipefail

# Usage: ./tag_release_1_01.sh [branch]
BRANCH="${1:-main}"
PATCH_FILE="${PATCH_FILE:-./release_1_01.patch}"

echo ">> Checking repo state..."
git rev-parse --is-inside-work-tree >/dev/null

echo ">> Switching to branch: ${BRANCH}"
git checkout -B "${BRANCH}"

echo ">> Dry-run applying patch..."
git apply --check "${PATCH_FILE}"

echo ">> Applying patch..."
git apply --whitespace=fix "${PATCH_FILE}"

echo ">> Committing changes..."
git add -A
git commit -m "Release 1.01: universal trade-mode (simulated/real devnet/mainnet)" || echo "No changes to commit"

echo ">> Tagging v1.01..."
git tag -a v1.01 -m "Release 1.01 — universal trade-mode switch"

echo ">> Pushing branch + tags..."
git push origin "${BRANCH}" --tags

echo "✅ Done."
