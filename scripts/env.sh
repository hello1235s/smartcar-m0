#!/usr/bin/env bash
export SMARTCAR_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source /opt/ros/humble/setup.bash
if [ -f "$SMARTCAR_ROOT/install_ros/setup.bash" ]; then source "$SMARTCAR_ROOT/install_ros/setup.bash"; fi
export PYTHONPATH="$SMARTCAR_ROOT/M5/M5-1:$SMARTCAR_ROOT/common:$PYTHONPATH"
