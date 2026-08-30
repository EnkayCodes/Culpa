#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> python packages"
pip install -e ".[dev]"

echo "==> claude code cli (the Agent SDK shells out to it)"
if ! command -v claude >/dev/null; then
  echo "  'claude' missing. Install: npm install -g @anthropic-ai/claude-code"
  echo "  then run 'claude' once and log in with your Claude account."
fi

echo "==> foundry"
if ! command -v forge >/dev/null; then
  echo "  Foundry missing. Install: curl -L https://foundry.paradigm.xyz | bash && foundryup"
  exit 1
fi

echo "==> forge-std into the proofground"
forge install --root proofground foundry-rs/forge-std --no-git || \
  (mkdir -p proofground/lib && git clone --depth 1 https://github.com/foundry-rs/forge-std proofground/lib/forge-std)

echo "==> solc versions (for the old-solc cases)"
if command -v solc-select >/dev/null; then
  solc-select install 0.4.24 0.4.25 0.5.16 0.6.12 0.7.6 0.8.20 0.8.23 || true
else
  echo "  solc-select missing (pip install solc-select) — only matters for old-solc cases"
fi

echo "==> run every committed reference exploit"
culpa verify || echo "(expected to fail until forge-std is in place; run 'culpa verify' again afterwards)"

echo "done. Next: cp .env.example .env, then 'culpa check'"
