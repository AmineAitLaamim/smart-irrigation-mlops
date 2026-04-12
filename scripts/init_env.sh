#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Smart Irrigation System — Generate .env
# =============================================================================
# Copies .env.example to .env if it doesn't already exist.
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_EXAMPLE="$PROJECT_ROOT/.env.example"
ENV_FILE="$PROJECT_ROOT/.env"

if [[ ! -f "$ENV_EXAMPLE" ]]; then
    echo "Error: .env.example not found in project root"
    exit 1
fi

if [[ -f "$ENV_FILE" ]]; then
    echo ".env already exists — remove it first to regenerate"
    echo "  rm .env"
    exit 0
fi

cp "$ENV_EXAMPLE" "$ENV_FILE"
echo "Created .env from .env.example"
echo ""
echo "Replace all 'changeme' values before starting services:"
echo ""
grep -n '=changeme' "$ENV_FILE" || echo "  (all values look good)"
