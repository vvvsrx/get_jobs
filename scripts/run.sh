#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

# Check if setup is needed
if [ ! -d "static" ]; then
    echo "First run detected. Running setup..."
    python3 scripts/setup.py
fi

echo "Starting GetJobs server..."
python3 run.py
