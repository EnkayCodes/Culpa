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

echo "== python + culpa =="
pip install -e ".[dev]"
solc-select install 0.8.20 0.4.24 0.5.16 0.6.12 0.7.6 || true
solc-select use 0.8.20 || true

echo "== smoke =="
culpa check || true
culpa verify || echo "(verify needs the reference exploits to compile — read the error above)"

echo
echo "Next:  echo 'GEMINI_API_KEY=your-key' >> .env   then   culpa consult"
