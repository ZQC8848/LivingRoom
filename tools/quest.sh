#!/usr/bin/env bash
# Preview Living Room on a Quest over USB -- no LAN, no certificate.
#
#   tools/quest.sh          # forward the port and start the dev server
#   tools/quest.sh --no-server   # only (re)do the port forward, e.g. after replugging
#
# The Quest browser opens http://localhost:5174, which `adb reverse` tunnels over USB to this
# Mac. localhost is a secure context, so WebXR works on plain HTTP. The Quest still needs its
# own internet (Wi-Fi) for the Orbis/LingBot WebRTC stream; only the page and /api go over USB.
#
# One-time setup: Quest developer mode (Meta Horizon phone app -> device -> Developer mode),
# `brew install android-platform-tools`, a USB-C data cable, "Allow USB debugging" in the headset.
# Debug the headset's page from this Mac at chrome://inspect.

set -euo pipefail
PORT=5174
cd "$(dirname "$0")/.."

if ! command -v adb >/dev/null; then
  echo "adb not found. Install it with:  brew install android-platform-tools" >&2
  exit 1
fi

adb start-server >/dev/null
devices=$(adb devices | awk 'NR > 1 && $2 == "device" {print $1}')
unauth=$(adb devices | awk 'NR > 1 && $2 == "unauthorized" {print $1}')
if [ -n "$unauth" ]; then
  echo "Quest connected but not authorised: put the headset on and accept 'Allow USB debugging'." >&2
  exit 1
fi
if [ -z "$devices" ]; then
  echo "No Quest found over USB. Check: developer mode on, a data (not charge-only) cable, headset awake." >&2
  exit 1
fi
if [ "$(echo "$devices" | wc -l | tr -d ' ')" -gt 1 ]; then
  echo "More than one device; using the first: $(echo "$devices" | head -1)" >&2
fi
serial=$(echo "$devices" | head -1)

adb -s "$serial" reverse "tcp:$PORT" "tcp:$PORT"
echo "Forwarded Quest localhost:$PORT -> Mac localhost:$PORT ($(adb -s "$serial" shell getprop ro.product.model | tr -d '\r'))"
echo
echo "In the headset: Browser -> http://localhost:$PORT -> Go live (or the VR panel) -> Enter VR"
echo "Debug from this Mac: chrome://inspect"
echo

if [ "${1:-}" = "--no-server" ]; then exit 0; fi
if lsof -iTCP:$PORT -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Dev server already running on :$PORT"
else
  exec npm --prefix web run dev:local
fi
