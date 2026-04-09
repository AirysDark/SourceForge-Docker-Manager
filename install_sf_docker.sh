#!/bin/bash
# install_sf_docker.sh
# One-shot installer for SourceForge-Docker-Manager
# Termux: uninstall existing Python, install prebuilt Python 3.10, then use prebuilt wheels

# ----------------------------
# Configuration
# ----------------------------
GITHUB_REPO="https://github.com/AirysDark/SourceForge-Docker-Manager.git"
INSTALL_DIR="$HOME/sf_docker_manager"
WHEEL_URL="https://github.com/AirysDark/SourceForge-Docker-Manager/releases/download/1.0.0/sf_docker_wheels_termux.tar.gz"
WHEEL_DIR="$HOME/sf_docker_wheels"
PYTHON_VERSION="3.10.14"
PYTHON_PREFIX="$HOME/.localpython310"

# Prebuilt Python tarball URL for Termux/arm64
PYTHON_TAR_URL="https://github.com/AirysDark/SourceForge-Docker-Manager/releases/download/1.0.0/Python-${PYTHON_VERSION}-termux-arm64.tar.gz"

# ----------------------------
# Detect Termux
# ----------------------------
IS_TERMUX=false
if [ -f "/data/data/com.termux/files/usr/bin/termux-info" ] || [ "$PREFIX" != "" ]; then
    IS_TERMUX=true
    echo "[INFO] Termux environment detected."
fi

# ----------------------------
# Step 0: Install build essentials & Rust for Termux
# ----------------------------
if [ "$IS_TERMUX" = true ]; then
    echo "[INFO] Installing Termux build essentials..."
    pkg update -y
    pkg install -y clang make git curl pkg-config libffi libcrypt libcrypt-dev zlib zlib-dev xz xz-utils wget tar rust
fi

# ----------------------------
# Step 0a: Remove existing Python (optional)
# ----------------------------
if [ "$IS_TERMUX" = true ]; then
    echo "[INFO] Removing system Python (will install Python 3.10 locally)..."
    pkg uninstall -y python python-pip
fi

# ----------------------------
# Step 0b: Download and install prebuilt Python 3.10
# ----------------------------
if [ ! -d "$PYTHON_PREFIX" ]; then
    echo "[INFO] Downloading prebuilt Python 3.10..."
    mkdir -p "$PYTHON_PREFIX"
    wget -O /tmp/Python-${PYTHON_VERSION}-termux-arm64.tar.gz "$PYTHON_TAR_URL"
    echo "[INFO] Extracting Python..."
    tar -xzf /tmp/Python-${PYTHON_VERSION}-termux-arm64.tar.gz -C "$PYTHON_PREFIX"
fi

export PATH="$PYTHON_PREFIX/bin:$PATH"
PYTHON_BIN="$PYTHON_PREFIX/bin/python3"
PIP_BIN="$PYTHON_PREFIX/bin/pip3"

# Verify Python version
PY_VER=$($PYTHON_BIN -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
REQUIRED_VER="3.10"
if [[ "$PY_VER" < "$REQUIRED_VER" ]]; then
    echo "[ERROR] Failed to install Python 3.10. Found $PY_VER"
    exit 1
fi
echo "[INFO] Python $PY_VER ready."

# Upgrade pip, wheel, setuptools
$PYTHON_BIN -m pip install --upgrade pip wheel setuptools

# ----------------------------
# Step 1: Clone or update SourceForge-Docker-Manager
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
# Step 2: Install pip dependencies
# ----------------------------
if [ "$IS_TERMUX" = true ]; then
    echo "[INFO] Termux detected: using prebuilt wheels..."
    mkdir -p "$WHEEL_DIR"
    curl -L "$WHEEL_URL" -o "$WHEEL_DIR/sf_docker_wheels_termux.tar.gz"
    tar -xzvf "$WHEEL_DIR/sf_docker_wheels_termux.tar.gz" -C "$WHEEL_DIR"
    echo "[INFO] Installing wheels offline..."
    $PIP_BIN install --no-index --find-links="$WHEEL_DIR" -r requirements.txt || {
        echo "[WARN] Prebuilt wheels failed, installing from source..."
        $PIP_BIN install -r requirements.txt
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
# Step 3: Install SourceForge-Docker-Manager package
# ----------------------------
echo "[INFO] Installing SourceForge-Docker-Manager package..."
$PIP_BIN install --user -e .

# ----------------------------
# Step 4: Completion
# ----------------------------
echo "[DONE] SourceForge-Docker-Manager installed!"
echo "You can now run the CLI via: sf-docker <command>"
