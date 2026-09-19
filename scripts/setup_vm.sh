#!/bin/bash
# ==============================================================================
# Provisionnement d'une VM GCP Ubuntu pour ce projet.
# ==============================================================================
# Exécuté par `make vm_setup`, qui envoie ce script sur la VM puis l'y exécute.
#
# Historiquement, ce script installait pyenv + pyenv-virtualenv et créait un
# virtualenv nommé, dont le nom et la version de Python étaient passés en
# arguments. Le projet est passé à uv : `uv sync` lit `.python-version`,
# télécharge l'interpréteur correspondant et installe les dépendances dans
# .venv. Il n'y a donc plus ni version ni nom d'environnement à transmettre.
set -euo pipefail

echo "🚀 Provisionnement de la VM..."

# --- 1. Paquets système ---
# build-essential n'est plus requis pour compiler CPython (uv télécharge des
# binaires précompilés), mais reste utile dès qu'une dépendance a du code natif.
echo "📦 Installation des paquets système..."
sudo apt-get update
sudo apt-get install -y make curl git zsh direnv

# --- 2. ZSH & Oh My Zsh ---
if [ ! -d "$HOME/.oh-my-zsh" ]; then
    sh -c "$(curl -fsSL https://raw.github.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended
fi

# --- 3. uv ---
# uv REMPLACE pyenv ET pyenv-virtualenv : il gère lui-même les versions de
# Python. Rien à installer via apt, un seul binaire statique suffit.
if ! command -v uv >/dev/null 2>&1 && [ ! -x "$HOME/.local/bin/uv" ]; then
    echo "🐍 Installation de uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

export PATH="$HOME/.local/bin:$PATH"

# Rendre uv disponible dans les shells suivants. L'installateur ajoute parfois
# la ligne lui-même : on vérifie avant d'écrire, pour ne pas la dupliquer à
# chaque provisionnement.
if [ -f "$HOME/.zshrc" ] && ! grep -q "local/bin" "$HOME/.zshrc"; then
    cat >> "$HOME/.zshrc" << 'EOF'

# uv — gestionnaire d'environnements Python du projet
export PATH="$HOME/.local/bin:$PATH"
EOF
fi

# --- 4. Plugins ZSH ---
if [ -f "$HOME/.zshrc" ]; then
    sed -i 's/plugins=(git)/plugins=(git uv ssh-agent direnv)/' "$HOME/.zshrc"
fi

echo
echo "✅ Provisionnement terminé."
echo
echo "👉 Prochaines étapes, SUR la VM :"
echo "   1. git clone <url-de-ton-repo> && cd <nom-du-repo>"
echo "   2. make local_setup      # uv sync : installe Python et les dépendances"
echo "   3. Ouvrir un nouveau shell (ou 'source ~/.zshrc') pour avoir uv dans le PATH"
