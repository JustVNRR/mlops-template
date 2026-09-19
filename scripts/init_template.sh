#!/bin/bash

# 1. Load variables from the .env file
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
else
    echo "❌ .env file not found. Please copy .env.sample to .env first."
    exit 1
fi

# Verify that PACKAGE_NAME is defined
if [ -z "$PACKAGE_NAME" ]; then
    echo "❌ The PACKAGE_NAME variable is not defined in the .env file."
    exit 1
fi

OLD_NAME="package_folder"
NEW_NAME=$PACKAGE_NAME

if [ "$OLD_NAME" == "$NEW_NAME" ]; then
    echo "⚠️ The package is already named $OLD_NAME. Nothing to do."
    exit 0
fi

echo "🔄 Initializing template: replacing '$OLD_NAME' with '$NEW_NAME'..."

# 2. Search and replace in files (Mac & Linux compatible)
# Ignore hidden folders like .git or virtual environments
# NOTE: *.toml covers pyproject.toml, which holds the package name in three
# places (name, packages, known-first-party).
find . -type f \( -name "*.py" -o -name "*.md" -o -name "Dockerfile" -o -name "*.toml" -o -name "Makefile" -o -name "*.mk" -o -name "*.sh" -o -name "*.yml" -o -name "*.yaml" \) -not -path "*/\.*" -not -path "*/venv/*" -not -path "*/.venv/*" | while read file; do
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # Syntax for macOS
        sed -i "" "s/$OLD_NAME/$NEW_NAME/g" "$file"
    else
        # Syntax for Linux (Ubuntu, Debian, WSL)
        sed -i "s/$OLD_NAME/$NEW_NAME/g" "$file"
    fi
done

# 3. Update .dockerignore specifically
if [ -f .dockerignore ]; then
    echo "📄 Updating .dockerignore..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i "" "s/$OLD_NAME/$NEW_NAME/g" .dockerignore
    else
        sed -i "s/$OLD_NAME/$NEW_NAME/g" .dockerignore
    fi
fi

# 4. Rename the main folder if it still exists under the old name
if [ -d "$OLD_NAME" ]; then
    mv "$OLD_NAME" "$NEW_NAME"
    echo "📁 Folder renamed to $NEW_NAME/"
fi

# 5. Regenerate uv.lock: it embeds the package name, so it goes stale the
#    moment the package is renamed. A stale lock makes `uv sync --frozen`
#    (used by the Dockerfile) fail outright.
if [ -f uv.lock ]; then
    if command -v uv >/dev/null 2>&1; then
        echo "🔒 Regenerating uv.lock for '$NEW_NAME'..."
        uv lock || { echo "⚠️  uv lock failed — removing uv.lock (regenerate it with 'make local_setup')."; rm -f uv.lock; }
    else
        echo "⚠️  uv not found — removing uv.lock (regenerate it with 'make local_setup')."
        rm -f uv.lock
    fi
fi

# ==============================================================================
# 💥 SELF-DESTRUCTION & CLEANUP
# ==============================================================================
echo "🗑️  Cleaning up initialization files..."

# 6. Remove the 'init_project' command from make/local.mk
if [ -f "make/local.mk" ]; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i "" "/init_project:/d" make/local.mk
        sed -i "" "/scripts\/init_template\.sh/d" make/local.mk
    else
        sed -i "/init_project:/d" make/local.mk
        sed -i "/scripts\/init_template\.sh/d" make/local.mk
    fi
fi

# 7. Delete the initialization script itself
rm scripts/init_template.sh

# (Optional) Remove the scripts folder if it's empty
# rmdir scripts 2>/dev/null || true

echo "✅ Initialization complete! Welcome to $PACKAGE_NAME."
