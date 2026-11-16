#!/usr/bin/env bash
set -eo pipefail
cd "$(dirname "$0")/.."
export PATH="$HOME/.local/bin:$PATH"
if [ ! -d .venv-model ]; then uv venv --python /usr/bin/python3 --seed .venv-model; fi
if ! .venv-model/bin/python -c 'import torch, torchvision' >/dev/null 2>&1; then
  uv pip install --python .venv-model/bin/python --index-url https://download.pytorch.org/whl/cpu 'torch==2.6.0' 'torchvision==0.21.0'
fi
uv pip install --python .venv-model/bin/python --index-url "${SMARTCAR_PYPI_INDEX:-https://pypi.org/simple}" 'numpy==1.26.4' 'onnx==1.17.0' 'onnxruntime==1.20.1' 'ultralytics==8.3.49' 'opencv-python==4.10.0.84' PyYAML matplotlib psutil pytest
