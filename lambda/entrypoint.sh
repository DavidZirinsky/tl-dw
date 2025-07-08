#!/bin/sh
set -e

# 1) Start the Mullvad daemon in the background
#    This binary is installed by the Debian package.
mullvad-daemon &

# 2) Wait for the daemon’s RPC socket to appear
echo "Waiting for Mullvad daemon…"
while ! mullvad status >/dev/null 2>&1; do
  sleep 0.5
done
echo "Mullvad daemon ready."

# 3) Connect your VPN using your account number
#    Assumes MULLVAD_ACCOUNT is set in env
mullvad connect

# 4) Wait until connected
echo "Waiting for VPN connection…"
while ! mullvad status | grep -q Connected; do
  sleep 1
done
echo "VPN is up!"

# 5) Now start your app
exec uvicorn lambda_function:app --host 0.0.0.0 --port "${PORT:-8080}"
