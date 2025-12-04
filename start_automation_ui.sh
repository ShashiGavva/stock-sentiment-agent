#!/bin/bash

# Start Automation Control Panel UI

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "========================================"
echo "Day Trading Automation Control Panel"
echo "========================================"
echo ""

cd "$SCRIPT_DIR"
source .venv312/bin/activate

echo "🚀 Starting web interface..."
echo ""
echo "Open in browser: http://localhost:5002"
echo ""
echo "Press Ctrl+C to stop"
echo ""

python automation_ui.py
