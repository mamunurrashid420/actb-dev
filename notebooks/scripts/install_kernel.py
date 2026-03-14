"""Install the actBI Jupyter kernel."""

import json
import sys
from pathlib import Path


def cleanup_stale_kernels():
    """Remove stale Jupyter runtime files that may reference old paths."""
    runtime_dir = Path.home() / ".local" / "share" / "jupyter" / "runtime"
    if not runtime_dir.exists():
        return

    cleaned = 0
    for kernel_file in runtime_dir.glob("kernel-*.json"):
        try:
            content = kernel_file.read_text()
            # Remove runtime files referencing old paths (data/analysis, etc.)
            if "data/analysis" in content or "kernel_launcher.py" in content:
                kernel_file.unlink()
                cleaned += 1
        except (OSError, PermissionError):
            pass

    if cleaned:
        print(f"Cleaned {cleaned} stale kernel runtime files")


def install_kernel():
    """Install the actBI kernel to the venv's Jupyter kernels directory."""
    # Clean up any stale runtime files first
    cleanup_stale_kernels()

    script_dir = Path(__file__).resolve().parent
    notebooks_dir = script_dir.parent
    launcher = notebooks_dir / "src" / "notebooks" / "kernel_launcher.py"

    kernel_spec = {
        "argv": [sys.executable, str(launcher), "-f", "{connection_file}"],
        "display_name": "actBI",
        "language": "python",
    }

    # Install to venv's kernel directory (project-local)
    kernels_dir = Path(sys.prefix) / "share" / "jupyter" / "kernels"
    kernel_dir = kernels_dir / "actbi"
    kernel_dir.mkdir(parents=True, exist_ok=True)

    kernel_json = kernel_dir / "kernel.json"
    kernel_json.write_text(json.dumps(kernel_spec, indent=2))

    print(f"Installed: {kernel_json}")
    print(f"Python: {sys.executable}")
    print(f"Launcher: {launcher}")


if __name__ == "__main__":
    install_kernel()
