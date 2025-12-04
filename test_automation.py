"""
Test script to verify automation setup
"""
import os
import sys
from datetime import datetime
import pytz

print("\n" + "=" * 70)
print("AUTOMATION SETUP TEST")
print("=" * 70)

# Check timezone
CST = pytz.timezone('America/Chicago')
current_time = datetime.now(CST)
print(f"✅ Current time (CST): {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")

# Check directories
print("\n📁 Checking directories...")
data_dir = "data"
logs_dir = "logs"

if os.path.exists(data_dir):
    print(f"✅ {data_dir}/ exists")
else:
    os.makedirs(data_dir)
    print(f"✅ {data_dir}/ created")

if os.path.exists(logs_dir):
    print(f"✅ {logs_dir}/ exists")
else:
    os.makedirs(logs_dir)
    print(f"✅ {logs_dir}/ created")

# Check required modules
print("\n📦 Checking required packages...")
try:
    import pandas
    print("✅ pandas")
except ImportError:
    print("❌ pandas - run: pip install pandas")

try:
    import numpy
    print("✅ numpy")
except ImportError:
    print("❌ numpy - run: pip install numpy")

try:
    import yfinance
    print("✅ yfinance")
except ImportError:
    print("❌ yfinance - run: pip install yfinance")

try:
    import schedule
    print("✅ schedule")
except ImportError:
    print("❌ schedule - run: pip install schedule")

try:
    import pytz
    print("✅ pytz")
except ImportError:
    print("❌ pytz - run: pip install pytz")

try:
    import pickle
    print("✅ pickle (built-in)")
except ImportError:
    print("❌ pickle")

# Check model files
print("\n🤖 Checking ML models...")
import config

if os.path.exists(config.CLF_PATH):
    print(f"✅ Classification model: {config.CLF_PATH}")
else:
    print(f"❌ Classification model not found: {config.CLF_PATH}")
    print("   Run model training first!")

if os.path.exists(config.Q90_PATH):
    print(f"✅ Regression model: {config.Q90_PATH}")
else:
    print(f"❌ Regression model not found: {config.Q90_PATH}")
    print("   Run model training first!")

# Check scripts
print("\n📜 Checking automation scripts...")
scripts = [
    "automation_scheduler.py",
    "start_automation.sh",
    "stop_automation.sh",
    "run_automation_foreground.sh",
    "com.daytrading.automation.plist"
]

for script in scripts:
    if os.path.exists(script):
        print(f"✅ {script}")
    else:
        print(f"❌ {script} - missing!")

# Check if scripts are executable
print("\n🔐 Checking script permissions...")
bash_scripts = [
    "start_automation.sh",
    "stop_automation.sh",
    "run_automation_foreground.sh"
]

for script in bash_scripts:
    if os.path.exists(script):
        is_executable = os.access(script, os.X_OK)
        if is_executable:
            print(f"✅ {script} is executable")
        else:
            print(f"⚠️  {script} not executable - run: chmod +x {script}")

# Test imports from automation_scheduler
print("\n🔍 Testing automation_scheduler imports...")
try:
    from features import build_features
    print("✅ features.build_features")
except ImportError as e:
    print(f"❌ features.build_features - {e}")

try:
    from symbols import get_sp500_tickers
    print("✅ symbols.get_sp500_tickers")
except ImportError as e:
    print(f"❌ symbols.get_sp500_tickers - {e}")

try:
    from utils import is_valid_stock
    print("✅ utils.is_valid_stock")
except ImportError as e:
    print(f"❌ utils.is_valid_stock - {e}")

try:
    from intraday_features import build_intraday_features, generate_day_trading_signals
    print("✅ intraday_features")
except ImportError as e:
    print(f"❌ intraday_features - {e}")

# Summary
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print("If all checks pass, you can start the automation with:")
print("  ./start_automation.sh")
print("\nOr run in foreground for testing:")
print("  ./run_automation_foreground.sh")
print("\nTo manually test components, uncomment test calls at the bottom of")
print("automation_scheduler.py and run:")
print("  python automation_scheduler.py")
print("=" * 70)
