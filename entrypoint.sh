#!/bin/bash
set -e

mkdir -p /root/.ssh
chmod 700 /root/.ssh

if [ ! -f /root/.ssh/id_rsa ]; then
    echo "Generating SSH key for host connection..."
    ssh-keygen -t rsa -b 2048 -f /root/.ssh/id_rsa -N "" -q
    echo "SSH key generated at /root/.ssh/id_rsa"
    echo "PUBLIC KEY (add to host authorized_keys):"
    cat /root/.ssh/id_rsa.pub
fi

echo "Starting application..."
exec "$@"

