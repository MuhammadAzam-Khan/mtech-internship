#!/bin/bash
# ==============================================================
#  High-Dimensional Data Explorer (v2) - Mac/Linux launcher
#  Run this from a terminal with:  ./run_mac_linux.sh
#  (first time only, you may need:  chmod +x run_mac_linux.sh)
# ==============================================================

# Move into the folder this script lives in, so it works no matter
# where it's run from.
cd "$(dirname "$0")"

echo "Checking for Python..."

if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
elif command -v python &> /dev/null; then
    PYTHON_CMD=python
else
    echo ""
    echo "ERROR: Python was not found on this computer."
    echo "Please install Python from https://www.python.org/downloads/"
    echo ""
    exit 1
fi

echo "Found Python ($PYTHON_CMD). Installing/checking required packages..."

# Try a normal install first. Some systems (e.g. recent Ubuntu/Debian,
# or Homebrew Python on Mac) block system-wide pip installs and print
# an "externally-managed-environment" error -- if that happens, we
# quietly retry with --user instead of leaving the user staring at
# a scary-looking error message.
if ! $PYTHON_CMD -m pip install -r requirements.txt --quiet 2>/tmp/hdde_pip_error.log; then
    echo "Standard install was blocked by this system, retrying safely..."
    if ! $PYTHON_CMD -m pip install -r requirements.txt --user --quiet 2>>/tmp/hdde_pip_error.log; then
        echo ""
        echo "Could not install packages automatically. Please run this manually:"
        echo "    $PYTHON_CMD -m pip install -r requirements.txt --user"
        echo ""
        echo "(Details saved to /tmp/hdde_pip_error.log)"
        echo "Attempting to start the program anyway in case packages are already installed..."
    fi
fi

echo ""
echo "Starting High-Dimensional Data Explorer..."
echo ""
$PYTHON_CMD main.py

echo ""
echo "Program closed."
