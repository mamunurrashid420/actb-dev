#!/bin/bash
# Start Jupyter Lab for actBI notebooks
#
# Usage: ./start.sh
#
# Select the 'actBI' kernel in your notebooks.
# The kernel auto-initializes with pandas, numpy, duckdb, and shared.data.

cd "$(dirname "$0")"

echo "Starting actBI Jupyter Lab..."
echo "Select 'actBI' kernel in your notebooks"

uv run jupyter lab
