import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).resolve().parents[2] / "pages" / "4_Stock_Portfolio.py"))
