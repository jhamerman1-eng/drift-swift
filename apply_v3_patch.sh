#!/usr/bin/env bash
set -euo pipefail

PATCH_FILE="${1:-drift_bots_v3_0.patch}"

# Ensure we're at the root of your repo before running this.
git checkout -b release/v3.0 || git checkout release/v3.0

git apply --whitespace=fix "$PATCH_FILE"
git add -A
git commit -m "v3.0: Orchestrator + JIT/Hedge/Trend scaffold, health/metrics, Swift driver"
git tag -a v3.0 -m "Drift Bots v3.0"

echo "✅ Applied and committed v3.0. Push with:"
echo "   git push origin release/v3.0 --tags"
