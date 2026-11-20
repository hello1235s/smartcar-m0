#!/usr/bin/env bash
task_restore_nounset=0
if [[ $- == *u* ]]; then task_restore_nounset=1; set +u; fi
export SMARTCAR_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source /opt/ros/humble/setup.bash
if [ -f "$SMARTCAR_ROOT/install_ros/setup.bash" ]; then
  source "$SMARTCAR_ROOT/install_ros/setup.bash"
fi
export PYTHONPATH="$SMARTCAR_ROOT/M3/common${PYTHONPATH:+:$PYTHONPATH}"
if [ "$task_restore_nounset" = 1 ]; then set -u; fi
unset task_restore_nounset
