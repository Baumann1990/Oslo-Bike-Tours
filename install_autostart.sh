#!/bin/bash
# Installs serve.js as a macOS login service so it starts automatically on boot.
# Run once from Terminal: bash ~/Documents/oslo-tours/install_autostart.sh

set -e

PLIST_SRC="$HOME/Documents/oslo-tours/no.oslobiketours.serve.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/no.oslobiketours.serve.plist"

# Check node is where the plist expects it
if [ ! -f "/usr/local/bin/node" ]; then
  NODE_PATH=$(which node 2>/dev/null || echo "")
  if [ -z "$NODE_PATH" ]; then
    echo "ERROR: node not found. Install Node.js from https://nodejs.org first."
    exit 1
  fi
  echo "NOTE: node found at $NODE_PATH (not /usr/local/bin/node)."
  echo "Updating plist to use $NODE_PATH ..."
  sed -i '' "s|/usr/local/bin/node|$NODE_PATH|g" "$PLIST_SRC"
fi

cp "$PLIST_SRC" "$PLIST_DEST"
launchctl load "$PLIST_DEST"
echo "Done. serve.js will now start automatically at login."
echo "To check it's running: curl -s http://localhost:3456/ | head -c 100"
echo "To stop it: launchctl unload $PLIST_DEST"
