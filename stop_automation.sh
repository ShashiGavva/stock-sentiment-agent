#!/bin/bash

# Stop Day Trading Automation Scheduler

LAUNCHD_PLIST="$HOME/Library/LaunchAgents/com.daytrading.automation.plist"

echo "========================================"
echo "Day Trading Automation - Stop"
echo "========================================"

# Check if running
if ! launchctl list | grep -q "com.daytrading.automation"; then
    echo "⚠️  Automation is not running"
    exit 0
fi

# Unload the service
echo "🛑 Stopping automation scheduler..."
launchctl unload "$LAUNCHD_PLIST"

# Remove plist
if [ -f "$LAUNCHD_PLIST" ]; then
    rm "$LAUNCHD_PLIST"
fi

# Check if successful
sleep 1
if launchctl list | grep -q "com.daytrading.automation"; then
    echo "❌ Failed to stop automation"
    exit 1
else
    echo "✅ Automation stopped successfully"
fi
