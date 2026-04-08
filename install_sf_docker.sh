#!/bin/bash
# install_sf_docker.sh
# One-shot installer for SourceForge-Docker-Manager

# ----------------------------
# Configuration
# ----------------------------
GITHUB_REPO="https://github.com/AirysDark/SourceForge-Docker-Manager.git"
INSTALL_DIR="$HOME/sf_docker_manager"
PYTHON_BIN=$(which python3 || echo "python3")
PIP_BIN=$(which pip3 || echo "pip3")

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
if [ -f "requirements.txt" ]; then
    echo "[INFO] Installing dependencies..."
    $PIP_BIN install --user -r requirements.txt
else
    echo "[WARN] requirements.txt not found, skipping"
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