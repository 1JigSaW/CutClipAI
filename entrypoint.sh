#!/bin/bash
set -e

eval "$(dbus-launch --sh-syntax)"

export DBUS_SESSION_BUS_ADDRESS
export DBUS_SESSION_BUS_PID

echo "DBUS started: $DBUS_SESSION_BUS_ADDRESS"

exec "$@"

