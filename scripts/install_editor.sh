#!/usr/bin/env bash
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
project="$HOME/smartcar-m0"
mkdir -p "$HOME/.local/opt/vscode" "$HOME/.local/bin" "$HOME/.local/share/applications"
if ! command -v code >/dev/null 2>&1; then
    curl -fLsS --connect-timeout 15 --max-time 120 --retry 3 --retry-all-errors --retry-max-time 240 -C - \
      https://update.code.visualstudio.com/latest/linux-x64/stable \
      -o "$project/evidence/vscode-linux-x64.tar.gz"
    tar -xzf "$project/evidence/vscode-linux-x64.tar.gz" --strip-components=1 -C "$HOME/.local/opt/vscode"
    ln -s "$HOME/.local/opt/vscode/bin/code" "$HOME/.local/bin/code"
fi
cat > "$HOME/.local/share/applications/smartcar-code.desktop" <<EOF
[Desktop Entry]
Name=Visual Studio Code
Comment=Smart car development
Exec=$HOME/.local/opt/vscode/code %F
Icon=$HOME/.local/opt/vscode/resources/app/resources/linux/code.png
Type=Application
Categories=Development;IDE;
Terminal=false
EOF
code --version
for extension in ms-python.python ms-vscode.cpptools ms-vscode-remote.remote-ssh ms-vscode-remote.remote-wsl; do
    code --install-extension "$extension"
done
code --list-extensions
