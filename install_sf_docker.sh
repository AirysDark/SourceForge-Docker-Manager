#!/bin/bash
# install_sf_docker.sh
# One-shot installer for SourceForge-Docker-Manager
# Termux: forcibly installs Python 3.10 from TUR + manual modules

# ----------------------------
# Configuration
# ----------------------------
GITHUB_REPO="https://github.com/AirysDark/SourceForge-Docker-Manager.git"
INSTALL_DIR="$HOME/sf_docker_manager"
REQUIREMENTS="requirements.txt"

# Default Python/Pip
PYTHON_BIN=$(command -v python3.10 || echo "python3")
PIP_BIN="$PYTHON_BIN -m pip"

# ----------------------------
# Step 0: Detect Termux
# ----------------------------
IS_TERMUX=false
if [ -f "/data/data/com.termux/files/usr/bin/termux-info" ]; then
    IS_TERMUX=true
    echo "[INFO] Termux environment detected."
fi

# ----------------------------
# Step 0b: Force install Python 3.10 via TUR (Termux)
# ----------------------------
if [ "$IS_TERMUX" = true ]; then
    echo "[INFO] Forcing installation of Python 3.10 from Termux repository (TUR)..."

    # Update packages and add TUR repo
    pkg update -y
    pkg install -y tur-repo

    # Force install Python 3.10 + build essentials
    pkg install -y python3.10 clang make git curl libffi

    # Ensure pip is available for Python 3.10
    $PYTHON_BIN -m ensurepip --upgrade

    # Use TUR Python 3.10 for this session
    PYTHON_BIN=$(command -v python3.10)
    PIP_BIN="$PYTHON_BIN -m pip"
    export PATH="$(dirname $PYTHON_BIN):$PATH"

    PY_VER=$($PYTHON_BIN -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    echo "[INFO] Forced TUR Python version: $PY_VER"
fi

# ----------------------------
# Step 1: Clone or update repo
# ----------------------------
if [ -d "$INSTALL_DIR" ]; then
    echo "[INFO] Repo exists. Pulling latest changes..."
    cd "$INSTALL_DIR" || exit
    git pull
else
    echo "[INFO] Cloning SourceForge-Docker-Manager..."
    git clone "$GITHUB_REPO" "$INSTALL_DIR"
    cd "$INSTALL_DIR" || exit
fi

# ----------------------------
# Step 2: Verify Python 3.10+
# ----------------------------
PY_VER=$($PYTHON_BIN -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if [[ "$PY_VER" < "3.10" ]]; then
    echo "[ERROR] Python 3.10+ required. Found $PY_VER"
    exit 1
fi
echo "[INFO] Python version $PY_VER OK"

# ----------------------------
# Step 3: Install pip dependencies
# ----------------------------
echo "[INFO] Installing dependencies from requirements.txt..."
$PIP_BIN install --upgrade pip wheel setuptools
if [ -f "$REQUIREMENTS" ]; then
    $PIP_BIN install --user -r "$REQUIREMENTS"
else
    echo "[WARN] requirements.txt not found, skipping pip installs"
fi

# ----------------------------
# Step 4: Install manual Python modules
# ----------------------------
echo "[INFO] Installing manual Python modules..."
for mod in runtime_manager docker_support fs_snapshots image_manager network_manager registry engine_core; do
    if [ -d "./$mod" ]; then
        $PIP_BIN install --user -e "./$mod"
    fi
done

# ----------------------------
# Step 5: Completion message
# ----------------------------
echo "[DONE] SourceForge-Docker-Manager installed!"
echo "You can now run the CLI via: sf-docker <command>"
