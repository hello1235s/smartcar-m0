#!/usr/bin/env bash
# Official CycloneDDS + TF2 0.25.24 callback-lock fix; no sudo/system changes.
set -euo pipefail
task_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$task_root/vendor/m3-dds-debs" "$task_root/vendor/m3-dds"
cd "$task_root/vendor/m3-dds-debs"
mapfile -t packages < "$task_root/M3/runtime/navigation-packages.lock"
if [ "${1:-}" = '--offline' ]; then
  sha256sum -c packages.sha256
elif [ "$#" = 0 ]; then
  apt-get download "${packages[@]}"
else
  printf 'Usage: bash scripts/install_m3_runtime.sh [--offline]\n' >&2
  exit 2
fi
for task_deb in ./*.deb; do dpkg-deb -x "$task_deb" "$task_root/vendor/m3-dds"; done
sha256sum ./*.deb > "$task_root/vendor/m3-dds/packages.sha256"
cp "$task_root/vendor/m3-dds/packages.sha256" packages.sha256
for task_deb in ./*.deb; do dpkg-deb -f "$task_deb" Package Version; done > "$task_root/vendor/m3-dds/packages.txt"
source "$task_root/scripts/m3_nav_env.sh"
python3 -c 'import ctypes, os; ctypes.CDLL(os.path.join(os.environ["SMARTCAR_ROOT"], "vendor/m3-dds/opt/ros/humble/lib/libtf2.so")); print("M3 TF2 core0.25.24 ready")'
if ldd "$task_root/vendor/m3-dds/opt/ros/humble/lib/librmw_cyclonedds_cpp.so" | grep -q 'not found'; then
  printf 'Missing runtime dependency. See ldd output:\n' >&2
  ldd "$task_root/vendor/m3-dds/opt/ros/humble/lib/librmw_cyclonedds_cpp.so"
  exit 1
fi
python3 -c 'import rclpy; rclpy.init(); n=rclpy.create_node("m3_middleware_preflight"); print(rclpy.get_rmw_implementation_identifier()); n.destroy_node(); rclpy.shutdown()'
