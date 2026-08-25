#!/usr/bin/env bash
# Generate README screenshots, demo-preview.gif, and/or full demo MP4
# from the live Enterprise Agentic AI Playground.
#
# Usage:
#   ./scripts/demo/generate-media.sh
#   ./scripts/demo/generate-media.sh --screenshots
#   ./scripts/demo/generate-media.sh --preview
#   ./scripts/demo/generate-media.sh --video
#   LIVE_DEMO_URL=https://… ./scripts/demo/generate-media.sh --all
#
# Not run from CI. Live AI usage is intentionally bounded.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEMO_DIR="$ROOT/scripts/demo"

cd "$DEMO_DIR"

if [[ ! -d node_modules ]]; then
  npm install
fi

# Ensure Chromium is present even if postinstall was skipped.
npx playwright install chromium >/dev/null

exec npm run demo:media -- "$@"
