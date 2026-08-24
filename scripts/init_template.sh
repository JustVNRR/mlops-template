#!/bin/bash

# 1. Charger les variables du fichier .env
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
else
    echo "❌ Fichier .env introuvable. Copie .env.sample vers .env d'abord."
    exit 1
fi

# Vérifier que PACKAGE_NAME est bien défini
if [ -z "$PACKAGE_NAME" ]; then
    echo "❌ La variable PACKAGE_NAME n'est pas définie dans le .env"
    exit 1
fi

OLD_NAME="package_folder"
NEW_NAME=$PACKAGE_NAME

if [ "$OLD_NAME" == "$NEW_NAME" ]; then
    echo "⚠️ Le package s'appelle déjà $OLD_NAME. Rien à faire."
    exit 0
fi

echo "🔄 Initialisation du template : remplacement de '$OLD_NAME' par '$NEW_NAME'..."

# 2. Chercher et remplacer dans les fichiers (Mac & Linux compatibles)
# On ignore les dossiers cachés comme .git ou les environnements virtuels
find . -type f \( -name "*.py" -o -name "*.md" -o -name "Dockerfile" -o -name "setup.py" -o -name "Makefile" -o -name "*.mk" -o -name "*.sh" \) -not -path "*/\.*" -not -path "*/venv/*" | while read file; do
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # Syntax pour macOS
        sed -i "" "s/$OLD_NAME/$NEW_NAME/g" "$file"
    else
        # Syntax pour Linux (Ubuntu, Debian, WSL)
        sed -i "s/$OLD_NAME/$NEW_NAME/g" "$file"
    fi
done

# 3. Renommer le dossier principal s'il existe encore sous l'ancien nom
if [ -d "$OLD_NAME" ]; then
    mv "$OLD_NAME" "$NEW_NAME"
    echo "📁 Dossier renommé en $NEW_NAME/"
fi

echo "✅ Template prêt ! Ton projet s'appelle désormais $NEW_NAME."
