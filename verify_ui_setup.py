"""
Verify that the Automation UI is properly set up
"""
import os
import sys

print("\n" + "=" * 70)
print("AUTOMATION UI SETUP VERIFICATION")
print("=" * 70)

checks_passed = 0
checks_total = 0

def check(description, condition, fix_hint=""):
    global checks_passed, checks_total
    checks_total += 1
    if condition:
        print(f"✅ {description}")
        checks_passed += 1
        return True
    else:
        print(f"❌ {description}")
        if fix_hint:
            print(f"   Fix: {fix_hint}")
        return False

print("\n📁 Checking Files...")
check("automation_ui.py exists", os.path.exists("automation_ui.py"))
check("start_automation_ui.sh exists", os.path.exists("start_automation_ui.sh"))
check("start_automation_ui.sh is executable", os.access("start_automation_ui.sh", os.X_OK),
      "chmod +x start_automation_ui.sh")
check("templates directory exists", os.path.exists("templates"))
check("automation_control.html exists", os.path.exists("templates/automation_control.html"))

print("\n📦 Checking Python Packages...")
try:
    import flask
    check("Flask installed", True)
except ImportError:
    check("Flask installed", False, "pip install flask")

try:
    import pandas
    check("Pandas installed", True)
except ImportError:
    check("Pandas installed", False, "pip install pandas")

try:
    import yfinance
    check("yfinance installed", True)
except ImportError:
    check("yfinance installed", False, "pip install yfinance")

try:
    import pytz
    check("pytz installed", True)
except ImportError:
    check("pytz installed", False, "pip install pytz")

try:
    from dotenv import load_dotenv
    check("python-dotenv installed", True)
except ImportError:
    check("python-dotenv installed", False, "pip install python-dotenv")

print("\n🤖 Checking ML Models...")
check("models directory exists", os.path.exists("models"))
check("Classification model exists", os.path.exists("models/clf_lgbm_08.pkl"),
      "Copy from main repo or run train_models.py")
check("Regression model exists", os.path.exists("models/reg_q90_08.pkl"),
      "Copy from main repo or run train_models.py")

print("\n📂 Checking Data Directories...")
data_exists = os.path.exists("data")
check("data directory exists", data_exists, "mkdir data")
logs_exists = os.path.exists("logs")
check("logs directory exists", logs_exists, "mkdir logs")

print("\n📧 Checking Email Configuration...")
check(".env file exists", os.path.exists(".env"))
if os.path.exists(".env"):
    with open(".env", "r") as f:
        env_content = f.read()
    check("SMTP_HOST configured", "SMTP_HOST" in env_content)
    check("SMTP_USERNAME configured", "SMTP_USERNAME" in env_content)
    check("SMTP_PASSWORD configured", "SMTP_PASSWORD" in env_content)

print("\n📚 Checking Documentation...")
check("MASTER_README.md exists", os.path.exists("MASTER_README.md"))
check("UI_QUICKSTART.md exists", os.path.exists("UI_QUICKSTART.md"))
check("AUTOMATION_UI_GUIDE.md exists", os.path.exists("AUTOMATION_UI_GUIDE.md"))
check("START_HERE_NEW.md exists", os.path.exists("START_HERE_NEW.md"))

print("\n🔍 Checking Project Modules...")
try:
    import config
    check("config.py accessible", True)
except ImportError:
    check("config.py accessible", False, "Check that config.py exists")

try:
    from features import build_features
    check("features.py accessible", True)
except ImportError:
    check("features.py accessible", False, "Check that features.py exists")

try:
    from symbols import get_sp500_tickers
    check("symbols.py accessible", True)
except ImportError:
    check("symbols.py accessible", False, "Check that symbols.py exists")

try:
    from utils import is_valid_stock
    check("utils.py accessible", True)
except ImportError:
    check("utils.py accessible", False, "Check that utils.py exists")

try:
    from intraday_features import build_intraday_features
    check("intraday_features.py accessible", True)
except ImportError:
    check("intraday_features.py accessible", False, "Check that intraday_features.py exists")

print("\n" + "=" * 70)
print(f"RESULTS: {checks_passed}/{checks_total} checks passed")
print("=" * 70)

if checks_passed == checks_total:
    print("\n🎉 SUCCESS! Everything is set up correctly.")
    print("\n📋 Next Steps:")
    print("  1. Start the UI:")
    print("     ./start_automation_ui.sh")
    print("\n  2. Open in browser:")
    print("     http://localhost:5002")
    print("\n  3. Read the quick start:")
    print("     cat UI_QUICKSTART.md")
    print("\n✨ You're ready to start trading!")
else:
    print(f"\n⚠️  {checks_total - checks_passed} issues found. Please fix them and run this script again.")
    print("\nQuick Fixes:")
    print("  pip install flask pandas yfinance pytz python-dotenv")
    print("  chmod +x start_automation_ui.sh")
    print("  mkdir -p data logs models")
    sys.exit(1)

print("\n" + "=" * 70)
