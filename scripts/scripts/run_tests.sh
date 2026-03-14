#!/bin/bash
# Run tests for all packages in the monorepo in parallel
# Each package uses its own pyproject.toml with correct pythonpath
#
# Usage:
#   ./scripts/run_tests.sh           # Run all tests quietly
#   ./scripts/run_tests.sh -v        # Run all tests verbosely
#   ./scripts/run_tests.sh --help    # Show pytest help

# Create temp dir for exit codes
TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

run_tests() {
    local name=$1
    shift
    echo "=== Testing $name ==="
    local exit_code=0
    uv run pytest "$@" 2>&1 | sed "s/^/[$name] /" || exit_code=${PIPESTATUS[0]}

    # Exit code 5 = no tests collected (ok for packages with no tests yet)
    if [ $exit_code -eq 5 ]; then
        echo "[$name] No tests found (skipped)"
        exit_code=0
    elif [ $exit_code -ne 0 ]; then
        echo "=== FAILED: $name ==="
    fi

    # Write exit code to temp file
    echo $exit_code > "$TMPDIR/$name.exit"
}

# Run all test suites in parallel
run_tests "pipelines" pipelines/tests -n auto -m "not integration" -q "$@" &
run_tests "shared" shared/tests -n auto -q "$@" &
run_tests "agents" agents/tests -n auto -q "$@" &
run_tests "prompts" prompts/tests -n auto -q "$@" &
run_tests "analysis" analysis/tests -n auto -q "$@" &

# Wait for all background jobs
wait

# Collect exit codes
overall_exit=0
for name in pipelines shared agents prompts analysis; do
    if [ -f "$TMPDIR/$name.exit" ]; then
        code=$(cat "$TMPDIR/$name.exit")
        if [ "$code" -ne 0 ]; then
            overall_exit=1
        fi
    fi
done

if [ $overall_exit -eq 0 ]; then
    echo "=== All tests passed ==="
else
    echo "=== Some tests FAILED ==="
fi

exit $overall_exit
