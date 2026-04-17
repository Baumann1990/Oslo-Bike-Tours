#!/bin/bash
# Double-click this file in Finder to push Oslo Bike Tours to GitHub.

set -e
cd "$(dirname "$0")"

echo "==> Initialising git repo (safe to re-run)…"
git init

echo "==> Staging files (respecting .gitignore)…"
git add .

echo "==> Creating first commit…"
git commit -m "Initial commit: import Oslo Bike Tours site" || echo "   (nothing new to commit)"

echo "==> Naming the branch 'main'…"
git branch -M main

echo "==> Linking to GitHub remote…"
git remote remove origin 2>/dev/null || true
git remote add origin https://github.com/Baumann1990/Oslo-Bike-Tours.git

echo "==> Pushing to GitHub (a browser window may open to log you in)…"
git push -u origin main

echo ""
echo "Done. Open https://github.com/Baumann1990/Oslo-Bike-Tours to verify."
echo "(You can close this window.)"
