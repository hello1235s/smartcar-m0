#!/usr/bin/env bash
set -euo pipefail
task_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$task_root"
source scripts/env.sh
export QT_QPA_PLATFORM=xcb
task_mode="${1:-dynamic}"
if [ "$#" -gt 0 ]; then shift; fi
case "$task_mode" in
  dynamic)
    exec .venv-ros/bin/python M3/optimization/run_navigation_trial.py \
      --label live_dynamic --runs 1 --seed 900 --gui --viewer --hold-after 8 \
      --params M3/M3-4/config/planner_B_tuned_params.yaml \
      --obstacle-at 8.0,1.6 --delay 3 "$@" ;;
  static)
    exec .venv-ros/bin/python M3/optimization/run_navigation_trial.py \
      --label live_static --runs 1 --seed 900 --gui --viewer --hold-after 8 "$@" ;;
  square)
    exec .venv-ros/bin/python M3/optimization/run_square_trial.py \
      --label live_square --laps 1 --gui --hold-after 8 "$@" ;;
  mapping)
    exec .venv-ros/bin/python M3/optimization/run_mapping_trial.py "$@" ;;
  *)
    printf 'Usage: bash scripts/run_m3_demo.sh {dynamic|static|square|mapping} [options]\n' >&2
    exit 2 ;;
esac
