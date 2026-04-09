#!/bin/bash
# install_sf_docker.sh
# One-shot installer for SourceForge-Docker-Manager
# Termux: prebuilt Python 3.10 + prebuilt wheels if available

# ----------------------------
# Configuration
# ----------------------------
GITHUB_REPO="https://github.com/AirysDark/SourceForge-Docker-Manager.git"
INSTALL_DIR="$HOME/sf_docker_manager"
WHEEL_URL="https://github.com/AirysDark/SourceForge-Docker-Manager/releases/download/1.0.0/sf_docker_wheels_termux.tar.gz"
PREBUILT_PYTHON_URL="https://github.com/AirysDark/Termux-Python-Prebuilt/releases/download/3.10.14/python3.10-termux.tar.gz"
WHEEL_DIR="$HOME/sf_docker_wheels"
PYTHON_PREFIX="$HOME/.localpython310"

PYTHON_BIN=$(command -v python3 || echo "python3")
PIP_BIN=$(command -v pip3 || echo "pip3")

# ----------------------------
# Step 0: Detect Termux
# ----------------------------
IS_TERMUX=false
if [ -f "/data/data/com.termux/files/usr/bin/termux-info" ] || [ "$PREFIX" != "" ]; then
    IS_TERMUX=true
    echo "[INFO] Termux environment detected."
fi

# ----------------------------
# Step 0b: Install prebuilt Python 3.10 for Termux
# ----------------------------
if [ "$IS_TERMUX" = true ]; then
    echo "[INFO] Installing prebuilt Python 3.10 for Termux..."

    # Remove existing Python if any
    pkg uninstall -y python python-pip || true

    # Download prebuilt Python 3.10 tarball if not exists
    if [ ! -f "$HOME/python3.10-termux.tar.gz" ]; then
        echo "[INFO] Downloading prebuilt Python 3.10..."
        curl -L "$PREBUILT_PYTHON_URL" -o "$HOME/python3.10-termux.tar.gz"
    fi

    # Extract prebuilt Python
    mkdir -p "$PYTHON_PREFIX"
    tar -xzf "$HOME/python3.10-termux.tar.gz" -C "$PYTHON_PREFIX" --strip-components=1

    # Use the prebuilt Python for session
    export PATH="$PYTHON_PREFIX/bin:$PATH"
    PYTHON_BIN="$PYTHON_PREFIX/bin/python"
    PIP_BIN="$PYTHON_PREFIX/bin/pip"

    # Verify
    PY_VER=$($PYTHON_BIN -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    echo "[INFO] Using prebuilt Python version: $PY_VER"
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
# Step 2: Ensure Python 3.10+
# ----------------------------
PY_VER=$($PYTHON_BIN -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
REQUIRED_VER="3.10"
if [[ "$PY_VER" < "$REQUIRED_VER" ]]; then
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
    echo "[INFO] Downloading prebuilt wheels tarball..."
    curl -L "$WHEEL_URL" -o "$WHEEL_DIR/sf_docker_wheels_termux.tar.gz"
    echo "[INFO] Extracting wheels..."
    tar -xzvf "$WHEEL_DIR/sf_docker_wheels_termux.tar.gz" -C "$WHEEL_DIR"
    echo "[INFO] Installing wheels offline..."
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
# Step 4: Install editable package (console script)
# ----------------------------
echo "[INFO] Installing SourceForge-Docker-Manager package..."
$PIP_BIN install --user -e .

# ----------------------------
# Step 5: Completion message
# ----------------------------
echo "[DONE] SourceForge-Docker-Manager installed!"
echo "You can now run the CLI via: sf-docker <command>"
