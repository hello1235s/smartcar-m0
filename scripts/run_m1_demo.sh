#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
source scripts/env.sh
export ROS_DOMAIN_ID=71
export QT_QPA_PLATFORM=xcb
mode="${1:-chain}"
if [ "$#" -gt 0 ]; then shift; fi
case "$mode" in
  chain) exec ros2 launch smartcar_training bringup.launch.py namespace:="" "$@" ;;
  dual) exec ros2 launch smartcar_training dual_bringup.launch.py "$@" ;;
  projection) exec .venv-ros/bin/python scripts/verify_projection.py "$@" ;;
  performance) exec .venv-ros/bin/python M1/M1-4/measure_chain.py "$@" ;;
  verify) exec .venv-ros/bin/python scripts/verify_m1_acceptance_v2.py "$@" ;;
  *) printf 'Usage: bash scripts/run_m1_demo.sh {chain|dual|projection|performance|verify}\n' >&2; exit 2 ;;
esac
