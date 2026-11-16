#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
source scripts/env.sh
.venv-ros/bin/python -m pytest -q M5/M5-1/tests M5/M5-3/tests
env -u PYTHONPATH PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv-model/bin/python -m pytest -q M6/M6-4/tests
