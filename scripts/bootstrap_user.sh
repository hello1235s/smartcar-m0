#!/usr/bin/env bash
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
project="$HOME/smartcar-m0"
mkdir -p "$project" "$HOME/.local/bin" "$HOME/.local/opt"
if ! command -v uv >/dev/null 2>&1; then
    curl -fLsS --connect-timeout 15 --max-time 120 https://astral.sh/uv/install.sh -o "$project/evidence/uv-installer.sh"
    UV_NO_MODIFY_PATH=1 sh "$project/evidence/uv-installer.sh"
fi
uv --version
if ! grep -Fq '# smartcar-m0 user tools' "$HOME/.bashrc"; then
    printf '\n# smartcar-m0 user tools\nexport PATH="$HOME/.local/bin:$PATH"\n' >> "$HOME/.bashrc"
fi
cd "$project"
if [ ! -d .git ]; then
    git init -b codex/m0-training
fi
if [ ! -d .venv ]; then
    uv venv --python /usr/bin/python3 --seed
fi
uv pip install --python .venv/bin/python -r requirements-dev.txt
if [ ! -f "$HOME/.ssh/id_ed25519" ] && [ ! -f "$HOME/.ssh/id_ed25519.pub" ]; then
    ssh-keygen -t ed25519 -N '' -C 'smartcar-m0-ubuntu' -f "$HOME/.ssh/id_ed25519"
fi
printf '\nBOOTSTRAP COMPLETE\n'
