#!/usr/bin/env bash
set -eo pipefail
cd "$(dirname "$0")/.."
source /opt/ros/humble/setup.bash
python3 M3/generate_worlds.py
colcon --log-base log_ros build \
  --base-paths M1/M1-1/src M3/M3-1/src \
  --build-base build_ros --install-base install_ros --symlink-install \
  --cmake-args -DPython3_EXECUTABLE=/usr/bin/python3 -DCMAKE_BUILD_TYPE=Release
