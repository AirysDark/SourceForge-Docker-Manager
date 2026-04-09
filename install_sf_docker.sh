#!/bin/bash
# install_sf_docker.sh
# One-shot installer for SourceForge-Docker-Manager
# Termux-only: uses prebuilt Python 3.10 and wheels (Rust, PyYAML, FastAPI, Uvicorn, Docker, Pydantic)

# ----------------------------
# Configuration
# ----------------------------
GITHUB_REPO="https://github.com/AirysDark/SourceForge-Docker-Manager.git"
INSTALL_DIR="$HOME/sf_docker_manager"

# Prebuilt wheels (Python 3.10 / aarch64)
WHEEL_URL="https://github.com/AirysDark/SourceForge-Docker-Manager/releases/download/1.0.0/sf_docker_wheels_termux.tar.gz"
WHEEL_DIR="$HOME/sf_docker_wheels"

# Termux Python 3.10 package (prebuilt)
PYTHON_PKG_URL="https://termux.dev/python3.10_aarch64.tar.gz"
PYTHON_PREFIX="$HOME/.localpython310"

# ----------------------------
# Detect Termux
# ----------------------------
IS_TERMUX=false
if [ -f "/data/data/com.termux/files/usr/bin/termux-info" ] || [ "$PREFIX" != "" ]; then
    IS_TERMUX=true
    echo "[INFO] Termux environment detected."
fi

# ----------------------------
# Install prebuilt Python 3.10 (Termux)
# ----------------------------
if [ "$IS_TERMUX" = true ]; then
    echo "[INFO] Installing prebuilt Python 3.10 for Termux..."
    mkdir -p "$PYTHON_PREFIX"
    cd "$HOME"
    curl -L "$PYTHON_PKG_URL" -o python3.10-termux.tar.gz
    tar -xzf python3.10-termux.tar.gz -C "$PYTHON_PREFIX"
    export PATH="$PYTHON_PREFIX/bin:$PATH"
fi

# ----------------------------
# Set Python / Pip
# ----------------------------
PYTHON_BIN=$(command -v python || command -v python3)
PIP_BIN=$(command -v pip || command -v pip3)
PY_VER=$($PYTHON_BIN -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")

if [[ "$PY_VER" < "3.10" ]]; then
    echo "[ERROR] Python 3.10+ required. Found $PY_VER"
    exit 1
fi
echo "[INFO] Using Python version $PY_VER"

# ----------------------------
# Clone or update SourceForge-Docker-Manager
# ----------------------------
if [ -d "$INSTALL_DIR" ]; then
    echo "[INFO] Repo exists. Pulling latest changes..."
    cd "$INSTALL_DIR" || exit
    git pull
else
    echo "[INFO] Cloning SourceForge-Docker-
