"""Compatibility entry point for measured M3 experiments."""
import runpy
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
arguments=['--domain' if x=='--domain-base' else x for x in sys.argv[1:]]
script=ROOT/'M3/optimization/run_square_trial.py'
sys.argv=[str(script)]+['--laps', '10', '--label', 'qualified_feedback']+arguments
runpy.run_path(str(script),run_name="__main__")
