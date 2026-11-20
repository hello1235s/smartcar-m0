"""Evaluate current independent-truth trials; historical evaluator remains available."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).resolve().parents[2]/'optimization/analyze_qualification.py'),run_name='__main__')
