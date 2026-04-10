from pathlib import Path

APP_NAME = "Investment Dashboard"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
EXPORT_DIR = DATA_DIR / "exports"
INBOX_DIR = DATA_DIR / "inbox"

# Fixed upload filenames (overwrite these files each refresh cycle)
BOND_SOURCE_FILE = str(INBOX_DIR / "bond_source.xlsx")
BOND_SHEETS = ["Database_Bonds", "Database_Payback"]
STOCK_SOURCE_FILE = str(INBOX_DIR / "stock_source.xlsx")
STOCK_SHEETS = ["Database_Stock"]
FCN_SOURCE_FILE = str(INBOX_DIR / "fcn_source.xlsx")
FCN_SHEETS = ["Database_FCN List", "Database_FCN"]

# Deposit source remains unchanged for now
STOCK_HISTORY_START_DATE = "2025-12-30"
DEPOSIT_SOURCE_FILE = "/mnt/c/Users/ericarthuang/Downloads/PSA????????????????_202602.xlsx"
DEPOSIT_DETAIL_SHEETS = ["PDC-RMB08", "PDC-USD08", "ITC-RMB08", "ITC-USD08", "Sili-RMB08", "Sili-USD08"]
DEPOSIT_LOOKUP_SHEETS = ["????", "????", "PSA??08"]
DEPOSIT_FX_FALLBACK = 7.3

# Streamlit Cloud entry point — when Streamlit runs this file directly, delegate to app.py.
# Use __main__ guard so normal imports from app.py do not recurse, and Cloud entry stays stable.
if __name__ == "__main__":
    import sys as _sys

    _sys.path.insert(0, str(PROJECT_ROOT))
    from app import main as _main

    _main()
