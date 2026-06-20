#!/bin/bash
# Smart NOC - Log Generator Helper Script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT/services/log-generator"
source "$PROJECT_ROOT/venv/bin/activate"

# Pass all arguments to the log generator
python generate_logs.py "$@"
