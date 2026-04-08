#!/usr/bin/env bash
set -e

echo "==> Installing Python dependencies..."
pip3 install -r requirements.txt --quiet

echo "==> Installing Playwright Chromium browser..."
python3 -m playwright install chromium

echo "==> Starting Flask app at http://localhost:5000"
python3 app.py
