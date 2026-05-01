#!/bin/bash
set -e

# Change socket group to match jenkins user's docker group
if [ -S /var/run/docker.sock ]; then
    DOCKER_GID=$(getent group docker | cut -d: -f3)
    chown root:${DOCKER_GID} /var/run/docker.sock 2>/dev/null || true
fi

# Start Jenkins
exec /usr/local/bin/jenkins.sh "$@"
