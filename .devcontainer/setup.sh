#!/usr/bin/env bash
# Runs once when the Codespace / dev container is created. Fast network here — this all works.
set -e
cd "$(dirname "$0")/.."

echo "== Foundry =="
curl -L https://foundry.paradigm.xyz | bash
export PATH="$HOME/.foundry/bin:$PATH"
"$HOME/.foundry/bin/foundryup"
grep -q '.foundry/bin' ~/.bashrc || echo 'export PATH="$HOME/.foundry/bin:$PATH"' >> ~/.bashrc

echo "== forge-std =="
"$HOME/.foundry/bin/forge" install --root proofground foundry-rs/forge-std --no-git \
  || git clone --depth 1 https://github.com/foundry-rs/forge-std proofground/lib/forge-std

echo "== python + marlowe =="
pip install --user -e ".[dev]"
pip install --user solc-select
python -m solc_select.__main__ install 0.8.20 0.4.24 0.5.16 0.6.12 0.7.6 || true
python -m solc_select.__main__ use 0.8.20 || true

echo "== smoke =="
export PATH="$HOME/.local/bin:$HOME/.foundry/bin:$PATH"
marlowe check || true
marlowe verify || echo "(verify needs the reference exploits to compile — check the error)"

echo
echo "Done. Add your key:  echo 'GEMINI_API_KEY=...' >> .env"
echo "Then:  marlowe consult"
