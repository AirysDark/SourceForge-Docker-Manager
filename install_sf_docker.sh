#!/bin/bash
# install_sf_docker.sh
# Termux: forcibly installs Python 3.10 from TUR + manual modules

# ----------------------------
# Configuration
# ----------------------------
GITHUB_REPO="https://github.com/AirysDark/SourceForge-Docker-Manager.git"
INSTALL_DIR="$HOME/sf_docker_manager"
REQUIREMENTS="requirements.txt"

PYTHON_BIN="$HOME/.termux_python3.10/bin/python"
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
# Step 0b: Force install Python 3.10 from TUR
# ----------------------------
if [ "$IS_TERMUX" = true ]; then
    echo "[INFO] Forcing installation of Python 3.10 from TUR..."

    # Remove any existing Python
    pkg uninstall -y python python-pip || true

    # Update packages and ensure TUR repo
    pkg update -y
    pkg install -y tur-repo

    # Install Python 3.10 + essentials
    pkg install -y python3.10 clang make git curl libffi

    # Install pip if missing
    python3.10 -m ensurepip --upgrade

    # Force local session binary path
    mkdir -p "$HOME/.termux_python3.10/bin"
    ln -sf $(command -v python3.10) "$HOME/.termux_python3.10/bin/python"
    ln -sf $(command -v pip3) "$HOME/.termux_python3.10/bin/pip"

    export PATH="$HOME/.termux_python3.10/bin:$PATH"
    PYTHON_BIN="$HOME/.termux_python3.10/bin/python"
    PIP_BIN="$PYTHON_BIN -m pip"

    PY_VER=$($PYTHON_BIN -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    echo "[INFO] TUR Python forced to version: $PY_VER"
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
echo "[INFO] Installing pip dependencies..."
$PIP_BIN install --upgrade pip wheel setuptools
if [ -f "$REQUIREMENTS" ]; then
    $PIP_BIN install --user -r "$REQUIREMENTS"
else
    echo "[WARN] requirements.txt not found, skipping pip installs"
fi

# ----------------------------
# Step 5: Completion message
# ----------------------------
echo "[DONE] SourceForge-Docker-Manager installed!"
echo "You can now run the CLI via: sf-docker <command>"
