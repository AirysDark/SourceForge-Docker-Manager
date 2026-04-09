#!/bin/bash
# install_sf_docker.sh
# One-shot installer for SourceForge-Docker-Manager
# Supports Termux: installs Rust, build essentials, or uses prebuilt wheels if available

# ----------------------------
# Configuration
# ----------------------------
GITHUB_REPO="https://github.com/AirysDark/SourceForge-Docker-Manager.git"
INSTALL_DIR="$HOME/sf_docker_manager"
WHEEL_URL="https://github.com/AirysDark/SourceForge-Docker-Manager/releases/download/1.0.0/sf_docker_wheels_termux.tar.gz"
WHEEL_DIR="$HOME/sf_docker_wheels"

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
# Step 0a: Install Rust & build essentials if Termux
# ----------------------------
if [ "$IS_TERMUX" = true ]; then
    echo "[INFO] Installing Rust and build tools for Termux..."
    pkg update -y
    pkg install -y clang make git curl rust python python-pip libffi
fi

# ----------------------------
# Step 0b: Compile and install Python 3.10 locally (Termux)
# ----------------------------
if [ "$IS_TERMUX" = true ]; then
    echo "[INFO] Termux detected: installing Python 3.10 locally (isolated)..."

    # Install build essentials
    pkg update -y
    pkg install -y clang make git curl wget libffi bzip2 \
        libcrypt ncurses libsqlite \
        readline bzip2 tk

    # Local installation prefix
    PYTHON_PREFIX="$HOME/.localpython310"
    mkdir -p "$PYTHON_PREFIX"

    # Download Python 3.10.x source
    PYTHON_VERSION="3.10.14"
    cd /tmp
    wget https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz
    tar -xzf Python-${PYTHON_VERSION}.tgz
    cd Python-${PYTHON_VERSION}

    # Configure, compile, and install to local prefix
    ./configure --prefix="$PYTHON_PREFIX" --enable-optimizations --with-ensurepip=install
    make -j$(nproc)
    make install

    # Use local Python as 'python' only
    export PATH="$PYTHON_PREFIX/bin:$PATH"
    PYTHON_BIN="$PYTHON_PREFIX/bin/python"
    PIP_BIN="$PYTHON_PREFIX/bin/pip"

    # Symlink python3 → python for scripts that use python3
    ln -sf "$PYTHON_BIN" "$PYTHON_PREFIX/bin/python3"

    # Verify local installation
    PY_VER=$($PYTHON_BIN -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    echo "[INFO] Using local Python version: $PY_VER (system Python untouched)"
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
    echo "[INFO] Termux detected: using prebuilt wheels..."
    mkdir -p "$WHEEL_DIR"
    echo "[INFO] Downloading prebuilt wheels tarball..."
    curl -L "$WHEEL_URL" -o "$WHEEL_DIR/sf_docker_wheels_termux.tar.gz"
    echo "[INFO] Extracting wheels..."
    tar -xzvf "$WHEEL_DIR/sf_docker_wheels_termux.tar.gz" -C "$WHEEL_DIR"
    echo "[INFO] Installing wheels offline..."
    $PIP_BIN install --no-index --find-links="$WHEEL_DIR" -r requirements.txt || {
        echo "[WARN] Prebuilt wheels failed. Installing dependencies locally..."
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
