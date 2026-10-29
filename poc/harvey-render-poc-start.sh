#!/bin/sh
set -eu
cd /opt/harvey

# Start Harvey's native dashboard on its default loopback-only interface.
# Do not expose dashboard port 5555 to Render's public ingress.
python -m harvey dashboard >/tmp/harvey-dashboard.log 2>&1 &
HARVEY_PID=$!

# The only public endpoint is a non-sensitive readiness check.
# It reports ready only when the native dashboard is listening locally.
exec python /opt/poc/health_server.py
