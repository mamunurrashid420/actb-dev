"""actBI kernel launcher - entry point for Jupyter kernel."""

import sys
from pathlib import Path

# Add src to Python path so notebooks module is importable
SCRIPT_DIR = Path(__file__).resolve().parent
SRC_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SRC_DIR))

# Initialize environment before kernel starts
# Launch ipykernel
from ipykernel import kernelapp  # noqa: E402

import notebooks.kernel_init  # noqa: E402, F401

kernelapp.launch_new_instance()
