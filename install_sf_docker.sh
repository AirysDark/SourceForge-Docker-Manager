#!/bin/bash
# install_sf_docker.sh
# One-shot installer for SourceForge-Docker-Manager
# Termux: installs Python 3.10 from TUR and prebuilt wheels if available

# ----------------------------
# Configuration
# ----------------------------
GITHUB_REPO="https://github.com/AirysDark/SourceForge-Docker-Manager.git"
INSTALL_DIR="$HOME/sf_docker_manager"
WHEEL_URL="https://github.com/AirysDark/SourceForge-Docker-Manager/releases/download/1.0.0/sf_docker_wheels_termux.tar.gz"
WHEEL_DIR="$HOME/sf_docker_wheels"

# Default Python/Pip
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
# Step 0b: Install Python 3.10 via Termux User Repo (TUR)
# ----------------------------
if [ "$IS_TERMUX" = true ]; then
    PY_VER=$($PYTHON_BIN -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null) || PY_VER="0"
    if [[ "$PY_VER" < "3.10" ]]; then
        echo "[INFO] Installing Python 3.10 from Termux repository..."
        pkg update -y
        pkg install -y tur-repo
        pkg install -y python3.10 python3.10-pip rust clang make git curl libffi
        PYTHON_BIN=$(command -v python3.10)
        PIP_BIN=$(command -v pip3.10)
        export PATH="$(dirname $PYTHON_BIN):$PATH"
        PY_VER=$($PYTHON_BIN -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        echo "[INFO] Using Python version: $PY_VER"
    else
        echo "[INFO] Python 3.10+ already installed: $PY_VER"
        # Use the current Python
        PYTHON_BIN=$(command -v python3)
        PIP_BIN=$(command -v pip3)
    fi
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
    echo "[INFO] Termux detected: attempting prebuilt wheels..."
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
# Step 4: Install editable package (console script)
# ----------------------------
echo "[INFO] Installing SourceForge-Docker-Manager package..."
$PIP_BIN install --user -e .

# ----------------------------
# Step 5: Completion message
# ----------------------------
echo "[DONE] SourceForge-Docker-Manager installed!"
echo "You can now run the CLI via: sf-docker <command>"
