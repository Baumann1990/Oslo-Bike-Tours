#!/bin/bash
# ================================================================
# Oslo Bike Tours - Mac Scheduler Setup
# ================================================================
# Run this script ONCE to install the automated poster on your Mac.
# It will run poster.py twice daily (9:00 AM and 5:00 PM).
#
# Prerequisites:
#   1. Python 3 installed (check: python3 --version)
#   2. Install Python dependencies:
#      pip3 install google-auth google-auth-oauthlib google-auth-httplib2 \
#                   google-api-python-client requests anthropic pillow
#
#   3. Gmail OAuth credentials:
#      - Go to: https://console.cloud.google.com
#      - Create a project → Enable Gmail API
#      - Go to "Credentials" → Create OAuth 2.0 Client ID (Desktop app type)
#      - Download JSON and save as: ~/Documents/oslo-tours/gmail_credentials.json
#      - First run will open browser for Gmail authorization
#
#   4. Anthropic API key set in environment:
#      export ANTHROPIC_API_KEY="your-key-here"
#      (Or add to ~/.zshrc / ~/.bashrc)
#
# Usage:
#   chmod +x ~/Documents/oslo-tours/setup_mac_scheduler.sh
#   ~/Documents/oslo-tours/setup_mac_scheduler.sh

set -e

TOURS_DIR="$HOME/Documents/oslo-tours"
PLIST_DIR="$HOME/Library/LaunchAgents"
PLIST_NAME="no.oslobiketours.poster"
PLIST_FILE="$PLIST_DIR/$PLIST_NAME.plist"
PYTHON=$(which python3)
LOG_PATH="$TOURS_DIR/launchd_output.log"

echo "Setting up Oslo Bike Tours auto-poster..."
echo "Script dir: $TOURS_DIR"
echo "Python: $PYTHON"

mkdir -p "$PLIST_DIR"

cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
    "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$PLIST_NAME</string>

    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON</string>
        <string>$TOURS_DIR/poster.py</string>
    </array>

    <key>EnvironmentVariables</key>
    <dict>
        <key>ANTHROPIC_API_KEY</key>
        <string>${ANTHROPIC_API_KEY:-}</string>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>

    <key>StartCalendarInterval</key>
    <array>
        <dict>
            <key>Hour</key><integer>9</integer>
            <key>Minute</key><integer>0</integer>
        </dict>
        <dict>
            <key>Hour</key><integer>17</integer>
            <key>Minute</key><integer>0</integer>
        </dict>
    </array>

    <key>WorkingDirectory</key>
    <string>$TOURS_DIR</string>

    <key>StandardOutPath</key>
    <string>$LOG_PATH</string>

    <key>StandardErrorPath</key>
    <string>$LOG_PATH</string>

    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
EOF

echo "Installing launchd plist..."
launchctl unload "$PLIST_FILE" 2>/dev/null || true
launchctl load "$PLIST_FILE"

echo ""
echo "✅ Auto-poster installed and scheduled!"
echo "   Runs at: 9:00 AM and 5:00 PM daily"
echo ""
echo "To test it right now:"
echo "   python3 $TOURS_DIR/poster.py --test"
echo ""
echo "To check logs:"
echo "   tail -f $LOG_PATH"
echo ""
echo "To uninstall:"
echo "   launchctl unload $PLIST_FILE && rm $PLIST_FILE"
