#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/smartcar-m0"
printf '%s\n' '[ssh.github.com]:443 ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOMqqnkVzrm0SdG6UOoqKLsabgH5C9okWi0dh2l9GKJl' > "$HOME/.ssh/known_hosts_smartcar_github"
chmod 600 "$HOME/.ssh/known_hosts_smartcar_github"
git remote set-url origin ssh://git@ssh.github.com:443/hello1235s/smartcar-m0.git
git config core.sshCommand "ssh -i $HOME/.ssh/id_ed25519 -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=10 -o UserKnownHostsFile=$HOME/.ssh/known_hosts_smartcar_github -o StrictHostKeyChecking=yes"
git ls-remote origin
git push -u origin HEAD:refs/heads/codex/m0-training
