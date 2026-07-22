#!/usr/bin/env bash

set -euo pipefail

BUNDLE="synthaudit-py311-update.bundle"

echo "==> Checking repository..."

git status

echo "==> Verifying bundle exists..."

if [ ! -f "$BUNDLE" ]; then
    echo "ERROR: $BUNDLE not found."
    exit 1
fi

echo "==> Fetching update from bundle..."

git fetch "$BUNDLE" '+refs/*:refs/remotes/bundle/*'

echo "==> Looking for new commits..."

git log --oneline HEAD..bundle/main || true

echo "==> Fast-forwarding main..."

git merge --ff-only bundle/main

echo "==> Pushing to GitHub..."

git push origin main

echo
echo "==========================================="
echo "Python 3.11 migration applied successfully."
echo "==========================================="
echo
echo "Now check:"
echo "https://github.com/rvndye/synthaudit/actions"
