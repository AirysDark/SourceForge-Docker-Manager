#!/bin/bash
# install_sf_docker.sh
# One-shot installer for SourceForge-Docker-Manager
# Termux: forcibly installs Python 3.10 from TUR + prebuilt wheels

# ----------------------------
# Configuration
# ----------------------------
GITHUB_REPO="https://github.com/AirysDark/SourceForge-Docker-Manager.git"
INSTALL_DIR="$HOME/sf_docker_manager"
WHEEL_URL="https://github.com/AirysDark/SourceForge-Docker-Manager/releases/download/1.0.0/sf_docker_wheels_termux.tar.gz"
WHEEL_DIR="$HOME/sf_docker_wheels"

# Default Python/Pip
PYTHON_BIN=$(command -v python3.10 || echo "python3")
PIP_BIN="$PYTHON_BIN -m pip"

# ----------------------------
# Step 0: Detect Termux
# ----------------------------
IS_TERMUX=false
if [ -f "/data/data/com.termux/files/usr/bin/termux-info" ] || [ "$PREFIX" != "" ]; then
    IS_TERMUX=true
    echo "[INFO] Termux environment detected."
fi

# ----------------------------
# Step 0b: Force install Python 3.10 from TUR (Termux)
# ----------------------------
if [ "$IS_TERMUX" = true ]; then
    echo "[INFO] Installing Python 3.10 from Termux repository (TUR)..."

    # Update packages and add TUR repo
    pkg update -y
    pkg install -y tur-repo

    # Install Python 3.10 and build essentials (without python3.10-pip)
    pkg install -y python3.10 rust clang make git curl libffi

    # Ensure pip is available for Python 3.10
    $PYTHON_BIN -m ensurepip --upgrade

    # Set Python 3.10 as session default
    PYTHON_BIN=$(command -v python3.10)
    PIP_BIN="$PYTHON_BIN -m pip"
    export PATH="$(dirname $PYTHON_BIN):$PATH"

    PY_VER=$($PYTHON_BIN -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    echo "[INFO] Using Python version: $PY_VER"
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
if [ "$IS_TERMUX" = true ]; then
    echo "[INFO] Termux detected: installing prebuilt wheels..."
    mkdir -p "$WHEEL_DIR"
    curl -L "$WHEEL_URL" -o "$WHEEL_DIR/sf_docker_wheels_termux.tar.gz"
    tar -xzvf "$WHEEL_DIR/sf_docker_wheels_termux.tar.gz" -C "$WHEEL_DIR"
    $PIP_BIN install --no-index --find-links="$WHEEL_DIR" -r requirements.txt || {
        echo "[WARN] Prebuilt wheels failed. Installing dependencies from PyPI..."
        $PIP_BIN install --upgrade pip wheel setuptools
        $PIP_BIN install --user -r requirements.txt
    }
else
    if [ -f "requirements.txt" ]; then
        echo "[INFO] Installing dependencies from PyPI..."
        $PIP_BIN install --user -r requirements.txt
    else
        echo "[WARN] requirements.txt not found, skipping"
    fi
fi

# ----------------------------
# Step 4: Install editable package
# ----------------------------
echo "[INFO] Installing SourceForge-Docker-Manager package..."
$PIP_BIN install --user -e .

# ----------------------------
# Step 5: Completion
# ----------------------------
echo "[DONE] SourceForge-Docker-Manager installed!"
echo "You can now run the CLI via: sf-docker <command>"
