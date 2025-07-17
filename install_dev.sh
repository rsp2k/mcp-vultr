#!/bin/bash

# Development installation script for mcp-vultr
# This script installs the package in development mode for testing

set -e

echo "🔧 Installing mcp-vultr in development mode..."

# Change to package directory
cd "$(dirname "$0")"

# Check for uv first, fall back to pip
if command -v uv &> /dev/null; then
    echo "📦 Using uv for fast, modern dependency management..."
    
    # Sync dependencies with dev extras
    echo "🔄 Syncing dependencies..."
    uv sync --extra dev
    
    echo "✅ Installation complete!"
    echo ""
    echo "🚀 You can now run:"
    echo "   mcp-vultr --help"
    echo "   mcp-vultr server"
    echo ""
    echo "🧪 Run tests with:"
    echo "   uv run pytest"
    echo "   uv run python run_tests.py --all-checks"
    echo ""
    echo "🔧 Code quality tools:"
    echo "   uv run black src tests"
    echo "   uv run mypy src"
    echo ""
    
else
    echo "📦 Using pip (consider installing uv for faster dependency management)..."
    echo "   Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo ""
    
    # Check if we're in a virtual environment
    if [[ -z "$VIRTUAL_ENV" ]]; then
        echo "⚠️  Warning: Not in a virtual environment"
        echo "   Consider running: python -m venv .venv && source .venv/bin/activate"
        echo ""
    fi

    # Install in development mode
    echo "📦 Installing package dependencies..."
    pip install -e .

    echo "🧪 Installing development dependencies..."
    pip install -e .[dev]

    echo "✅ Installation complete!"
    echo ""
    echo "🚀 You can now run:"
    echo "   mcp-vultr --help"
    echo "   mcp-vultr server"
    echo ""
    echo "🧪 Run tests with:"
    echo "   pytest"
    echo "   python run_tests.py --all-checks"
    echo ""
fi

echo "📝 Set your API key:"
echo "   export VULTR_API_KEY='your-api-key-here'"
