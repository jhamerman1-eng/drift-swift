#!/usr/bin/env bash
set -euo pipefail
TAG="${1:-v1.17.0-rc2}"
MSG="Release candidate 2 scaffold for v1.17"
git add .
git commit -m "$MSG" || true
git tag -a "$TAG" -m "Release candidate 2 for 1.17"
git push origin main --tags
echo "Tagged $TAG and pushed to origin."
