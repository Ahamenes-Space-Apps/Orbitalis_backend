#!/usr/bin/env bash
# Run import-linter boundary contracts.
set -euo pipefail
uv run lint-imports
