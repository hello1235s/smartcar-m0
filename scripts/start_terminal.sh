#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
source scripts/env.sh
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-68}"
pids=()
cleanup() { for pid in "${pids[@]}"; do kill -INT "$pid" 2>/dev/null || true; done; wait || true; pids=(); }
trap 'cleanup; exit 0' INT TERM
trap cleanup EXIT
while true; do
install_ros/dashboard_tools/lib/dashboard_tools/dashboard_aggregator & pids+=("$!")
install_ros/smartcar_training/lib/smartcar_training/control_bridge & pids+=("$!")
.venv-ros/bin/python M6/M6-1/perception_node.py & pids+=("$!")
if [[ "${SMARTCAR_SOFTWARE_DEMO:-0}" == 1 ]]; then .venv-ros/bin/python M5/M5-2/simulator.py & pids+=("$!"); fi
.venv-ros/bin/python M5/M5-2/host_side/dashboard.py "$@" & pids+=("$!")
wait "${pids[-1]}" || true
cleanup
if [[ -f M5/.terminal_restart_requested ]]; then rm -- M5/.terminal_restart_requested; else break; fi
done
