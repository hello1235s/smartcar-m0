#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="$HOME/.local/bin:$PATH"
source .venv/bin/activate
mkdir -p evidence
python -m pytest M0/M0-2/tests M0/M0-3/tests M0/M0-4/tests -q | tee evidence/all_tests.log
python M0/M0-2/corr_tool.py --config M0/M0-2/config.yaml | tee evidence/m02_sample_result.log
python M0/M0-3/sensor_analyzer.py --input M0/M0-3/sensor_data.csv --output M0/M0-3/cleaned_data.csv | tee evidence/m03_final_result.log
python M0/M0-4/scheduler.py --config M0/M0-4/tasks_demo.yaml --timeout 15 --report M0/M0-4/report.json --seed 42 --color always | tee evidence/m04_demo.log
set +e
python M0/M0-4/scheduler.py --config M0/M0-4/tasks_failure.yaml --report evidence/m04_failure_report.json --seed 42 | tee evidence/m04_failure.log
failure_code=${PIPESTATUS[0]}
python M0/M0-4/scheduler.py --config M0/M0-4/tasks_timeout.yaml --report evidence/m04_timeout_report.json | tee evidence/m04_timeout.log
timeout_code=${PIPESTATUS[0]}
set -e
test "$failure_code" -eq 1
test "$timeout_code" -eq 124
bash M0/M0-1/check_env.sh | tee evidence/environment_check.log
printf '\nALL LOCAL ACCEPTANCE CHECKS PASSED\n'
