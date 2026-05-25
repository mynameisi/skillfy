#!/usr/bin/env bash
# Full sync user-built skills to external registries (Notion / Feishu).
#
# Usage:
#   sync-external-datasources.sh check
#   sync-external-datasources.sh sync --target notion|feishu|all [extra_roots...]

set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
exec python3 "$DIR/sync_external.py" "$@"
