#!/usr/bin/env bash
# Compatibility entry; install the complete qualified M3 runtime.
exec bash "$(dirname "${BASH_SOURCE[0]}")/install_m3_runtime.sh" "$@"
