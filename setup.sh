#!/bin/bash
set -e

cd "$(dirname "$0")"

python3 -m venv .venv
source .venv/bin/activate
pip install matplotlib numpy geopy timezonefinder

echo ""
echo "Setup terminé. Lance ./run.sh pour démarrer."
