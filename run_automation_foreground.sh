#!/bin/bash

# Run Day Trading Automation in foreground (for testing/debugging)

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "========================================"
echo "Day Trading Automation - Foreground"
echo "========================================"
echo "Running in foreground (Ctrl+C to stop)"
echo "========================================"
echo ""

cd "$SCRIPT_DIR"
source .venv312/bin/activate
python automation_scheduler.py
