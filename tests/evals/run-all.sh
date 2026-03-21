#!/usr/bin/env bash
# Run all eval tests from the repository root.
# Usage: bash tests/evals/run-all.sh
#        bash tests/evals/run-all.sh --run-llm-evals
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

exec python3 -m pytest "${REPO_ROOT}/tests/evals/" -v "$@"
