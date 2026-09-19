#!/bin/bash
# ==============================================================================
# Provisioning a GCP Ubuntu VM for this project.
# ==============================================================================
# Run by `make vm_setup`, which uploads this script to the VM and executes it
# there.
#
# Historically this script installed pyenv + pyenv-virtualenv and created a
# named virtualenv, whose name and Python version were passed as arguments.
# The project moved to uv: `uv sync` reads `.python-version`, downloads the
# matching interpreter and installs the dependencies into .venv. There is
# therefore no longer any version or environment name to pass around.
set -euo pipefail

echo "🚀 Provisioning the VM..."

# --- 1. System packages ---
# build-essential is no longer needed to compile CPython (uv downloads
# prebuilt binaries), but it remains useful as soon as a dependency ships
# native code.
echo "📦 Installing system packages..."
sudo apt-get update
sudo apt-get install -y make curl git zsh direnv

# --- 2. ZSH & Oh My Zsh ---
if [ ! -d "$HOME/.oh-my-zsh" ]; then
    sh -c "$(curl -fsSL https://raw.github.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended
fi

# --- 3. uv ---
# uv REPLACES pyenv AND pyenv-virtualenv: it manages Python versions itself.
# Nothing to install through apt, a single static binary is enough.
if ! command -v uv >/dev/null 2>&1 && [ ! -x "$HOME/.local/bin/uv" ]; then
    echo "🐍 Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

export PATH="$HOME/.local/bin:$PATH"

# Make uv available in subsequent shells. The installer sometimes adds the line
# itself: we check before writing, so it is not duplicated on every provision.
if [ -f "$HOME/.zshrc" ] && ! grep -q "local/bin" "$HOME/.zshrc"; then
    cat >> "$HOME/.zshrc" << 'EOF'

# uv — the project's Python environment manager
export PATH="$HOME/.local/bin:$PATH"
EOF
fi

# --- 4. ZSH plugins ---
if [ -f "$HOME/.zshrc" ]; then
    sed -i 's/plugins=(git)/plugins=(git uv ssh-agent direnv)/' "$HOME/.zshrc"
fi

echo
echo "✅ Provisioning complete."
echo
echo "👉 Next steps, ON the VM:"
echo "   1. git clone <your-repo-url> && cd <repo-name>"
echo "   2. make local_setup      # uv sync: installs Python and the dependencies"
echo "   3. Open a new shell (or 'source ~/.zshrc') so uv is on your PATH"
