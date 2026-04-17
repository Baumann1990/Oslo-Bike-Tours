#!/bin/bash
# Push the Oslo Bike Tours site to GitHub.
# Run from Terminal with:  bash ~/Documents/oslo-tours/push-to-github.sh

set -e  # stop on any error

cd ~/Documents/oslo-tours

echo "==> Initialising git repo (safe to re-run)…"
git init

echo "==> Staging files (respecting .gitignore)…"
git add .

echo "==> Creating first commit…"
git commit -m "Initial commit: import Oslo Bike Tours site" || echo "   (nothing to commit — already committed)"

echo "==> Naming the branch 'main'…"
git branch -M main

echo "==> Linking to GitHub remote…"
git remote remove origin 2>/dev/null || true
git remote add origin https://github.com/Baumann1990/Oslo-Bike-Tours.git

echo "==> Pushing to GitHub (browser may open to log you in)…"
git push -u origin main

echo ""
echo "Done. Open https://github.com/Baumann1990/Oslo-Bike-Tours to verify."
