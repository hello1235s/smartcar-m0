#!/usr/bin/env bash
# Download apt-authenticated official ROS packages; no sudo or system changes.
set -euo pipefail
task_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$task_root/vendor/m3-dds-debs" "$task_root/vendor/m3-dds"
cd "$task_root/vendor/m3-dds-debs"
packages=(ros-humble-rmw-cyclonedds-cpp ros-humble-cyclonedds
  ros-humble-iceoryx-binding-c ros-humble-iceoryx-hoofs ros-humble-iceoryx-posh)
apt-get download "${packages[@]}"
for task_deb in ./*.deb; do dpkg-deb -x "$task_deb" "$task_root/vendor/m3-dds"; done
sha256sum ./*.deb > "$task_root/vendor/m3-dds/packages.sha256"
for task_deb in ./*.deb; do dpkg-deb -f "$task_deb" Package Version; done > "$task_root/vendor/m3-dds/packages.txt"
source "$task_root/scripts/m3_nav_env.sh"
if ldd "$task_root/vendor/m3-dds/opt/ros/humble/lib/librmw_cyclonedds_cpp.so" | grep -q 'not found'; then
  printf 'Missing runtime dependency. See ldd output:\n' >&2
  ldd "$task_root/vendor/m3-dds/opt/ros/humble/lib/librmw_cyclonedds_cpp.so"
  exit 1
fi
python3 -c 'import rclpy; rclpy.init(); n=rclpy.create_node("m3_middleware_preflight"); print(rclpy.get_rmw_implementation_identifier()); n.destroy_node(); rclpy.shutdown()'
