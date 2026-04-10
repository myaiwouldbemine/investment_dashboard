import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).resolve().parents[2] / "pages" / "3_Bond_Portfolio.py"))
