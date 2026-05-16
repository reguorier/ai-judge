#!/bin/zsh
set -euo pipefail

cd "$(dirname "$0")"
echo "AI Judge installer"
echo

if [[ ! -x ".venv/bin/python" ]]; then
  echo "Missing .venv/bin/python. Create the virtual environment before installing."
  exit 1
fi

".venv/bin/python" tools/install_mac_app.py

echo
echo "AI Judge is installed in ~/Applications."
