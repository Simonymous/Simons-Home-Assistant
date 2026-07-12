#!/bin/bash
# Syncs the live Home Assistant config from the SMB share into this local
# clone and pushes to GitHub. /Volumes/config is slow for git operations
# directly (SMB), so this repo lives on local disk instead; only a plain
# file copy (rsync) touches the network share, git never does.
#
# Usage: ./sync-and-push.sh "commit message"

set -euo pipefail
cd "$(dirname "$0")"

if [ -z "${1:-}" ]; then
  echo "Usage: $0 \"commit message\""
  exit 1
fi

SOURCE="/Volumes/config"

# NOTE: --delete mirrors this repo to match $SOURCE exactly, so anything
# that only exists locally (this script, .git/) MUST be excluded or it
# gets deleted on every run.
rsync -a --delete \
  --exclude "/sync-and-push.sh" \
  --exclude ".git/" \
  --exclude ".storage/" \
  --exclude "secrets.yaml" \
  --exclude "*.db" --exclude "*.db-shm" --exclude "*.db-wal" \
  --exclude "*.sqlite" --exclude "*.sqlite-shm" --exclude "*.sqlite-wal" \
  --exclude ".ha_run.lock" \
  --exclude "home-assistant.log*" \
  --exclude ".cache/" \
  --exclude ".cloud/" \
  --exclude "deps/" \
  --exclude "tts/" \
  --exclude "image/" \
  --exclude "www/community/" \
  --exclude "www/ha_washdata/preview/" \
  --exclude "__pycache__/" \
  --exclude "*.pyc" \
  --exclude "*.tar" --exclude "*.tar.gz" \
  --exclude "backups/" \
  --exclude ".vscode/" \
  --exclude ".claude/" \
  --exclude ".DS_Store" \
  "$SOURCE/" ./

git add -A
if git diff --cached --quiet; then
  echo "Nothing changed, nothing to commit."
  exit 0
fi

git commit -m "$1"
git push
