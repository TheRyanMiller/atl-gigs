#!/usr/bin/env bash
set -euo pipefail

if [ -f "venv/bin/activate" ]; then
  source venv/bin/activate
fi

pytest -q

cd atl-gigs
npm install
npm run test
npm run test:e2e
