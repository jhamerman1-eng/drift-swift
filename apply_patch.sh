#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
FILES_DIR="$HERE/files"

if [ ! -d ".git" ]; then
  echo "⚠️  No .git directory found. Initializing a new repo..."
  git init
fi

echo "➕ Copying files into repo..."
rsync -a --exclude '.DS_Store' "$FILES_DIR"/ ./

echo "📦 Staging changes..."
git add VERSION libs/ bots/ configs/ scripts/ tests/ Makefile pyproject.toml requirements.txt README_v0_9.md .env.example || true

echo "🌿 Creating release branch release/v0.9 (if missing)..."
if ! git rev-parse --verify release/v0.9 >/dev/null 2>&1; then
  git checkout -b release/v0.9
else
  git checkout release/v0.9
fi

echo "✅ Committing v0.9 relink files..."
git commit -m "v0.9 relink: scaffold + configs + metrics"

echo "🏷  Tagging v0.9.0..."
git tag -f v0.9.0

echo "✅ Done. You can now push: git push origin release/v0.9 --tags"
