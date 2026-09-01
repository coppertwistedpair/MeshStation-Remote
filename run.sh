#!/usr/bin/env bash
# Run MeshRX without having to remember the arch-specific runtime path.
# Any arguments are passed straight through to meshrx.py, e.g.:
#   ./run.sh --setup
#   ./run.sh --region US --preset LONG_FAST
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARCH="$(uname -m)"

case "$ARCH" in
  aarch64) PLATFORM="linux_aarch64" ;;
  x86_64)  PLATFORM="linux_x86_64" ;;
  *)
    echo "Unsupported architecture: $ARCH (only linux_aarch64 / linux_x86_64 are built)" >&2
    exit 1
    ;;
esac

RUNTIME="$DIR/install/$PLATFORM/runtime/bin/python"

if [[ ! -x "$RUNTIME" ]]; then
  echo "Runtime not found at $RUNTIME" >&2
  echo "Build it first:" >&2
  echo "  cd install/$PLATFORM && ./auto-engine-builder.sh" >&2
  exit 1
fi

exec "$RUNTIME" "$DIR/meshrx.py" "$@"
