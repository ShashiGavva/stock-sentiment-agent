#!/bin/bash

# Start Day Trading Automation Scheduler
# This script will start the automation in the background using launchd on macOS

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PLIST_FILE="$SCRIPT_DIR/com.daytrading.automation.plist"
LAUNCHD_PLIST="$HOME/Library/LaunchAgents/com.daytrading.automation.plist"

echo "========================================"
echo "Day Trading Automation - Start"
echo "========================================"

# Create logs directory
mkdir -p "$SCRIPT_DIR/logs"

# Check if already running
if launchctl list | grep -q "com.daytrading.automation"; then
    echo "⚠️  Automation is already running!"
    echo "   Use ./stop_automation.sh to stop it first."
    exit 1
fi

# Copy plist to LaunchAgents
echo "📋 Installing launchd service..."
cp "$PLIST_FILE" "$LAUNCHD_PLIST"

# Load the service
echo "🚀 Starting automation scheduler..."
launchctl load "$LAUNCHD_PLIST"

# Check if successful
sleep 2
if launchctl list | grep -q "com.daytrading.automation"; then
    echo "✅ Automation started successfully!"
    echo ""
    echo "📊 Schedule:"
    echo "   • 8:30 AM CST - Generate daily signals & populate watchlist"
    echo "   • 9:00 AM CST - Start day trading"
    echo "   • Every 5 min (9:00 AM - 3:00 PM CST) - Process signals"
    echo "   • 3:00 PM CST - Generate end-of-day digest"
    echo ""
    echo "📝 Logs: $SCRIPT_DIR/logs/automation.log"
    echo "🔴 Errors: $SCRIPT_DIR/logs/automation.error.log"
    echo ""
    echo "To stop: ./stop_automation.sh"
    echo "To check status: launchctl list | grep daytrading"
else
    echo "❌ Failed to start automation"
    echo "Check logs for errors: $SCRIPT_DIR/logs/automation.error.log"
    exit 1
fi
