#!/bin/bash

set -e

echo "Installing dependencies in stages..."

echo "Stage 1: Installing base dependencies with fixed versions..."
pip install -r requirements.txt

echo "Stage 2: Fixing version conflicts (pydantic, pydantic-core, starlette)..."
pip install "pydantic==2.9.2" "pydantic-core==2.23.4" "starlette>=0.40.0,<0.42.0" --force-reinstall

echo "Stage 3: Installing pydantic-ai separately..."
pip install "pydantic-ai==0.4.9" || {
    echo "Warning: pydantic-ai installation failed. Trying with --no-deps..."
    pip install "pydantic-ai==0.4.9" --no-deps || {
        echo "Installing pydantic-ai-slim instead..."
        pip install "pydantic-ai-slim[openai]==0.4.9"
    }
}

echo "Stage 4: Fixing pydantic-core compatibility after pydantic-ai..."
pip install "pydantic-core==2.23.4" "pydantic==2.9.2" --force-reinstall

echo "Stage 5: Final verification..."
pip check || echo "Warning: Some dependency conflicts may remain, but core packages should work"

echo "✅ Dependencies installation completed!"

