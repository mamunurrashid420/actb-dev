#!/usr/bin/env python3
"""Compile protobuf definitions to Python and TypeScript code.

Usage:
    python scripts/compile_protos.py

This script:
1. Finds all .proto files in src/xlake/proto/
2. Compiles them using grpc_tools.protoc (Python)
3. Compiles them using ts-proto (TypeScript)
4. Outputs Python to src/xlake/generated/
5. Outputs TypeScript to web/shared/src/generated/
6. Fixes imports and creates barrel exports
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path


def fix_python_imports(file_path: Path) -> None:
    """Fix generated imports to use xlake.generated prefix."""
    content = file_path.read_text()
    original = content

    # Fix imports like: from actbi.v1 import X -> from xlake.generated.actbi.v1 import X
    content = re.sub(
        r"^from actbi\.",
        "from xlake.generated.actbi.",
        content,
        flags=re.MULTILINE,
    )

    # Fix imports like: import actbi.v1.X -> import xlake.generated.actbi.v1.X
    content = re.sub(
        r"^import actbi\.",
        "import xlake.generated.actbi.",
        content,
        flags=re.MULTILINE,
    )

    if content != original:
        file_path.write_text(content)
        print(f"  Fixed imports in {file_path.name}")


def compile_python(proto_root: Path, proto_files: list[Path], output_dir: Path) -> bool:
    """Compile proto files to Python using grpc_tools.protoc."""
    print("\n--- Compiling Python ---")

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build protoc command
    cmd = [
        sys.executable,
        "-m",
        "grpc_tools.protoc",
        f"--proto_path={proto_root}",
        f"--python_out={output_dir}",
        f"--pyi_out={output_dir}",
    ]
    cmd.extend(str(pf) for pf in proto_files)

    print(f"Running: {' '.join(cmd[:6])} ...")

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error compiling Python protos: {e}")
        if e.stderr:
            print(e.stderr)
        return False

    # Fix imports in generated files
    print("Fixing imports in generated files...")
    for py_file in output_dir.rglob("*_pb2.py"):
        fix_python_imports(py_file)
    for pyi_file in output_dir.rglob("*_pb2.pyi"):
        fix_python_imports(pyi_file)

    # Create __init__.py files in output directories
    for init_dir in [
        output_dir,
        output_dir / "actbi",
        output_dir / "actbi" / "v1",
    ]:
        init_file = init_dir / "__init__.py"
        if not init_file.exists():
            init_file.write_text('"""Generated protobuf code."""\n')
            print(f"  Created {init_file.name}")

    print(f"Successfully compiled {len(proto_files)} proto files to Python")
    return True


def compile_typescript(
    proto_root: Path, proto_files: list[Path], output_dir: Path
) -> bool:
    """Compile proto files to TypeScript using ts-proto."""
    print("\n--- Compiling TypeScript ---")

    # Check if npx is available
    npx_path = shutil.which("npx")
    if not npx_path:
        print("Warning: npx not found, skipping TypeScript generation")
        print(
            "  Install Node.js and run 'npm install' in web/shared to enable TS generation"
        )
        return True  # Not a fatal error

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # ts-proto options for JSON support and clean interfaces
    ts_proto_opts = [
        "outputJsonMethods=true",  # Generate fromJSON/toJSON
        "esModuleInterop=true",  # ES module compatibility
        "snakeToCamel=true",  # Convert snake_case to camelCase
        "exportCommonSymbols=false",  # Don't export DeepPartial etc
        "outputEncodeMethods=false",  # We only need JSON, not binary
        "outputClientImpl=false",  # No gRPC client
    ]
    ts_proto_opt_str = ",".join(ts_proto_opts)

    # Build protoc command with ts-proto plugin via npx
    cmd = [
        npx_path,
        "protoc",
        f"--proto_path={proto_root}",
        f"--ts_proto_out={output_dir}",
        f"--ts_proto_opt={ts_proto_opt_str}",
    ]
    cmd.extend(str(pf) for pf in proto_files)

    print(f"Running: npx protoc --ts_proto_out={output_dir} ...")

    try:
        result = subprocess.run(
            cmd, check=True, capture_output=True, text=True, cwd=output_dir.parent
        )
        if result.stdout:
            print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error compiling TypeScript protos: {e}")
        if e.stderr:
            print(e.stderr)
        return False
    except FileNotFoundError:
        print("Warning: protoc or ts-proto not found, skipping TypeScript generation")
        print("  Run 'npm install -g ts-proto' or ensure protoc is in PATH")
        return True  # Not a fatal error

    # Create barrel export index.ts
    create_typescript_barrel(output_dir)

    print(f"Successfully compiled {len(proto_files)} proto files to TypeScript")
    return True


def create_typescript_barrel(output_dir: Path) -> None:
    """Create index.ts barrel export for all generated TypeScript files."""
    # Find all generated .ts files (excluding index.ts itself)
    ts_files = [
        f
        for f in output_dir.rglob("*.ts")
        if f.name != "index.ts" and not f.name.endswith(".d.ts")
    ]

    if not ts_files:
        print("  No TypeScript files found to export")
        return

    # Group by directory for organized exports
    exports: list[str] = []
    exports.append("// Auto-generated barrel export for protobuf types")
    exports.append("// Do not edit manually - regenerate with compile_protos.py")
    exports.append("")

    for ts_file in sorted(ts_files):
        # Calculate relative path from output_dir
        rel_path = ts_file.relative_to(output_dir)
        # Remove .ts extension for import
        import_path = "./" + str(rel_path.with_suffix(""))
        exports.append(f'export * from "{import_path}";')

    index_file = output_dir / "index.ts"
    index_file.write_text("\n".join(exports) + "\n")
    print(f"  Created barrel export: {index_file.name}")


def main() -> int:
    """Compile all proto files to Python and TypeScript."""
    # Resolve paths
    xlake_root = Path(__file__).parent.parent
    repo_root = xlake_root.parent
    proto_root = xlake_root / "src" / "xlake" / "proto"

    # Output directories
    python_output_dir = xlake_root / "src" / "xlake" / "generated"
    typescript_output_dir = repo_root / "web" / "shared" / "src" / "generated"

    # Find all .proto files
    proto_files = list(proto_root.rglob("*.proto"))

    if not proto_files:
        print("No .proto files found")
        return 1

    print(f"Found {len(proto_files)} proto files:")
    for pf in proto_files:
        print(f"  - {pf.relative_to(proto_root)}")

    # Compile to Python
    if not compile_python(proto_root, proto_files, python_output_dir):
        return 1

    # Compile to TypeScript
    if not compile_typescript(proto_root, proto_files, typescript_output_dir):
        return 1

    print("\n--- Done ---")
    print(f"Python output: {python_output_dir}")
    print(f"TypeScript output: {typescript_output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
