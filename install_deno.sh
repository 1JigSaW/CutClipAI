#!/bin/bash

set -e

echo "🦕 Checking Deno installation..."

if command -v deno &> /dev/null; then
    CURRENT_VERSION=$(deno --version | head -n 1 | awk '{print $2}')
    echo "✅ Deno is already installed: version $CURRENT_VERSION"
    
    echo "🔄 Updating Deno to latest version..."
    deno upgrade || echo "⚠️  Could not upgrade Deno (may already be latest)"
else
    echo "📦 Deno not found. Installing Deno..."
    
    curl -fsSL https://deno.land/install.sh | sh
    
    export DENO_INSTALL="$HOME/.deno"
    export PATH="$DENO_INSTALL/bin:$PATH"
    
    if ! grep -q "DENO_INSTALL" ~/.bashrc; then
        echo 'export DENO_INSTALL="$HOME/.deno"' >> ~/.bashrc
        echo 'export PATH="$DENO_INSTALL/bin:$PATH"' >> ~/.bashrc
    fi
    
    if [ -f ~/.zshrc ] && ! grep -q "DENO_INSTALL" ~/.zshrc; then
        echo 'export DENO_INSTALL="$HOME/.deno"' >> ~/.zshrc
        echo 'export PATH="$DENO_INSTALL/bin:$PATH"' >> ~/.zshrc
    fi
    
    echo "✅ Deno installed successfully!"
fi

if command -v deno &> /dev/null; then
    FINAL_VERSION=$(deno --version | head -n 1 | awk '{print $2}')
    echo "🎉 Deno version: $FINAL_VERSION"
    echo "📍 Deno location: $(which deno)"
else
    echo "❌ Error: Deno installation failed or not in PATH"
    exit 1
fi

echo "✅ Deno setup complete!"
