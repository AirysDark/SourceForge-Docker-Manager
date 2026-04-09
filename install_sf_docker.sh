#!/bin/bash
# install_sf_docker.sh
# One-shot installer for SourceForge-Docker-Manager
# Termux: installs Python 3.10 from TUR + prebuilt wheels
# Skips pydantic-core if no prebuilt wheel available

# ----------------------------
# Configuration
# ----------------------------
GITHUB_REPO="https://github.com/AirysDark/SourceForge-Docker-Manager.git"
INSTALL_DIR="$HOME/sf_docker_manager"
WHEEL_URL="https://github.com/AirysDark/SourceForge-Docker-Manager/releases/download/1.0.0/sf_docker_wheels_termux.tar.gz"
WHEEL_DIR="$HOME/sf_docker_wheels"

# Default Python/Pip
PYTHON_BIN=$(command -v python3.10 || command -v python3)
PIP_BIN="$PYTHON_BIN -m pip"

# ----------------------------
# Detect Termux
# ----------------------------
IS_TERMUX=false
if [ -f "/data/data/com.termux/files/usr/bin/termux-info" ] || [ "$PREFIX" != "" ]; then
    IS_TERMUX=true
    echo "[INFO] Termux environment detected."
fi

# ----------------------------
# Ensure Python 3.10 (Termux)
# ----------------------------
if [ "$IS_TERMUX" = true ]; then
    echo "[INFO] Installing Python 3.10 from Termux repository..."
    pkg update -y
    pkg install -y tur-repo
    pkg install -y python3.10 rust clang make git curl libffi
    PYTHON_BIN=$(command -v python3.10)
    PIP_BIN="$PYTHON_BIN -m pip"
    export PATH="$(dirname $PYTHON_BIN):$PATH"
fi

# Verify Python version
PY_VER=$($PYTHON_BIN -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if [[ "$PY_VER" < "3.10" ]]; then
    echo "[ERROR] Python 3.10+ required. Found $PY_VER"
    exit 1
fi
echo "[INFO] Python version $PY_VER OK"

# ----------------------------
# Clone or update repo
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
# Install prebuilt wheels (Termux)
# ----------------------------
if [ "$IS_TERMUX" = true ]; then
    echo "[INFO] Installing prebuilt Termux wheels..."
    mkdir -p "$WHEEL_DIR"
    curl -L "$WHEEL_URL" -o "$WHEEL_DIR/sf_docker_wheels_termux.tar.gz"
    tar -xzvf "$WHEEL_DIR/sf_docker_wheels_termux.tar.gz" -C "$WHEEL_DIR"

    # Temporarily remove pydantic-core from requirements.txt for Termux
    grep -v "pydantic-core" requirements.txt > requirements_no_pydantic.txt

    # Install wheels excluding pydantic-core
    $PIP_BIN install --no-index --find-links="$WHEEL_DIR" -r requirements_no_pydantic.txt || {
        echo "[WARN] Some prebuilt wheels failed. Installing remaining dependencies from PyPI..."
        $PIP_BIN install --upgrade pip wheel setuptools
        $PIP_BIN install --user -r requirements_no_pydantic.txt
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
# Install editable package
# ----------------------------
echo "[INFO] Installing SourceForge-Docker-Manager package..."
$PIP_BIN install --user -e .

# ----------------------------
# Completion
# ----------------------------
echo "[DONE] SourceForge-Docker-Manager installed!"
echo "Note: pydantic-core may need to be installed separately on Termux if required."
echo "You can now run the CLI via: sf-docker <command>"
