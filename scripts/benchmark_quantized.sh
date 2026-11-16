#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
for mode in dynamic static_qdq static_qoperator; do
  .venv-model/bin/python M6/M6-1/tools/benchmark.py --model "M6/M6-2/models/$mode.onnx" --source hardware/k230/smartcar_usb_20261116_200340 --out "M6/M6-2/results/benchmark_$mode"
done
