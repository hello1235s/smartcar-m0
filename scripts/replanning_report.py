"""Measure current recovery events; pass an explicit qualification manifest."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).resolve().parents[1]/'M3/optimization/replanning_report.py'),run_name='__main__')
