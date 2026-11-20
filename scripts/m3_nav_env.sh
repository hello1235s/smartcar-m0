#!/usr/bin/env bash
# Source this in a terminal used for Nav2; M1 and mapping keep scripts/env.sh.
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
task_dds_prefix="$SMARTCAR_ROOT/vendor/m3-dds/opt/ros/humble"
if [ ! -f "$task_dds_prefix/lib/librmw_cyclonedds_cpp.so" ]; then
  printf 'Run bash scripts/install_m3_runtime.sh first.\n' >&2
  return 1
fi
export LD_LIBRARY_PATH="$task_dds_prefix/lib:$task_dds_prefix/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export AMENT_PREFIX_PATH="$task_dds_prefix${AMENT_PREFIX_PATH:+:$AMENT_PREFIX_PATH}"
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI="file://$SMARTCAR_ROOT/M3/M3-3/config/cyclone_local.xml"
unset task_dds_prefix
