#!/usr/bin/env bash
set -euo pipefail

# release_rc2.sh — Automate commit, tag, and push for v1.17.0-rc2
# Usage:
#   ./release_rc2.sh /path/to/your/local/repo [/path/to/driftbot_v1_17_0_rc2.zip]
#
# - First arg: local Git repo directory (required)
# - Second arg: optional path to the RC2 zip; if provided, it will be unzipped into the repo root before committing.

REPO_DIR="${1:-}"
ZIP_PATH="${2:-}"

if [[ -z "${REPO_DIR}" ]]; then
  echo "ERROR: repo directory is required."
  echo "Usage: $0 /path/to/local/repo [/path/to/zip]"
  exit 1
fi

if [[ ! -d "${REPO_DIR}" ]]; then
  echo "ERROR: repo directory not found: ${REPO_DIR}"
  exit 1
fi

# Move to repo
cd "${REPO_DIR}"

# Ensure we're in a git repo
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "ERROR: ${REPO_DIR} is not a git repository."
  exit 1
fi

# Show current branch
CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
echo "Current branch: ${CURRENT_BRANCH}"
if [[ "${CURRENT_BRANCH}" != "main" ]]; then
  echo "WARNING: You are not on 'main' (current: ${CURRENT_BRANCH})."
  read -p "Continue anyway? [y/N] " yn
  case "$yn" in
    [Yy]*) ;;
    *) echo "Aborted."; exit 1;;
  esac
fi

# Optional unzip
if [[ -n "${ZIP_PATH}" ]]; then
  if [[ ! -f "${ZIP_PATH}" ]]; then
    echo "ERROR: zip file not found: ${ZIP_PATH}"
    exit 1
  fi
  echo "Unzipping ${ZIP_PATH} into repo root..."
  unzip -o "${ZIP_PATH}" -d .
fi

# Stage, commit, tag, push
echo "Staging changes..."
git add .

# If no changes, warn and continue (in case only tag is needed)
if git diff --cached --quiet; then
  echo "No staged changes. Proceeding to tag."
else
  echo "Committing..."
  git commit -m "Release candidate 2 scaffold for v1.17"
fi

TAG_NAME="v1.17.0-rc2"
TAG_MESSAGE="Release candidate 2 for v1.17"

# If tag exists locally, delete and recreate only with explicit confirmation
if git rev-parse "${TAG_NAME}" >/dev/null 2>&1; then
  echo "Tag ${TAG_NAME} already exists locally."
  read -p "Recreate local tag ${TAG_NAME}? This will delete and re-add it. [y/N] " yn
  case "$yn" in
    [Yy]*) git tag -d "${TAG_NAME}" ;;
    *) echo "Skipping tag creation."; TAG_NAME="";;
  esac
fi

if [[ -n "${TAG_NAME}" ]]; then
  echo "Creating tag ${TAG_NAME}..."
  git tag -a "${TAG_NAME}" -m "${TAG_MESSAGE}"
fi

echo "Pushing changes to origin ${CURRENT_BRANCH}..."
git push origin "${CURRENT_BRANCH}"

if [[ -n "${TAG_NAME}" ]]; then
  echo "Pushing tag ${TAG_NAME}..."
  git push origin "${TAG_NAME}"
fi

echo "Done. You can now draft the GitHub release for ${TAG_NAME} in the web UI."
