#!/bin/bash

# View current automation status and data

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "========================================"
echo "Day Trading Automation - Status"
echo "========================================"
echo ""

# Check if automation is running
echo "🔍 Service Status:"
if launchctl list | grep -q "com.daytrading.automation"; then
    echo "✅ Automation is RUNNING"
else
    echo "⚠️  Automation is STOPPED"
    echo "   Start with: ./start_automation.sh"
fi
echo ""

# Show watchlist
echo "📊 Today's Watchlist:"
if [ -f "data/automation_watchlist.json" ]; then
    python3 -c "
import json
with open('data/automation_watchlist.json', 'r') as f:
    data = json.load(f)
    print('  Symbols:', ', '.join(data.get('symbols', [])))
    print('  Generated:', data.get('generated_at', 'N/A'))
    print('  Total signals:', data.get('total_signals', 0))
"
else
    echo "  ⚠️  No watchlist file found (wait until 8:30 AM)"
fi
echo ""

# Show active positions
echo "💼 Active Positions:"
if [ -f "data/automation_positions.json" ]; then
    num_positions=$(python3 -c "
import json
with open('data/automation_positions.json', 'r') as f:
    data = json.load(f)
    print(len(data))
")
    if [ "$num_positions" -gt 0 ]; then
        python3 -c "
import json
with open('data/automation_positions.json', 'r') as f:
    data = json.load(f)
    for symbol, pos in data.items():
        print(f\"  {symbol}: {pos['shares']:.2f} shares @ \${pos['entry_price']:.2f} (Total: \${pos['total_invested']:.2f})\")
"
    else
        echo "  No open positions"
    fi
else
    echo "  ⚠️  No positions file found"
fi
echo ""

# Show today's trades
echo "📝 Today's Trades:"
if [ -f "data/automation_trades.json" ]; then
    num_trades=$(python3 -c "
import json
with open('data/automation_trades.json', 'r') as f:
    data = json.load(f)
    print(len(data))
")
    if [ "$num_trades" -gt 0 ]; then
        echo "  Total trades: $num_trades"
        python3 -c "
import json
with open('data/automation_trades.json', 'r') as f:
    data = json.load(f)
    buys = sum(1 for t in data if t['signal'] == 'BUY')
    sells = sum(1 for t in data if t['signal'] == 'SELL')
    total_pnl = sum(t.get('profit_loss', 0) for t in data if 'profit_loss' in t)
    print(f'  Buys: {buys}, Sells: {sells}')
    if total_pnl != 0:
        print(f'  Total P&L: \${total_pnl:+.2f}')
"
    else
        echo "  No trades executed today"
    fi
else
    echo "  ⚠️  No trades file found"
fi
echo ""

# Show digest if available
echo "📧 Latest Digest:"
if [ -f "data/daily_digest.txt" ]; then
    echo "  ✅ Digest available (view with: cat data/daily_digest.txt)"
    # Show first few lines
    head -n 20 data/daily_digest.txt
    echo "  ..."
    echo "  (Full digest: cat data/daily_digest.txt)"
else
    echo "  ⚠️  No digest file found (wait until 3:00 PM)"
fi
echo ""

# Show recent log activity
echo "📋 Recent Log Activity (last 10 lines):"
if [ -f "logs/automation.log" ]; then
    tail -n 10 logs/automation.log
else
    echo "  ⚠️  No log file found"
fi
echo ""

echo "========================================"
echo "Commands:"
echo "  ./start_automation.sh     - Start automation"
echo "  ./stop_automation.sh      - Stop automation"
echo "  tail -f logs/automation.log - Watch logs"
echo "  cat data/daily_digest.txt - View full digest"
echo "========================================"
