#!/bin/bash
# WoeidChat Launcher Script

MODE="${1:-both}"

case "$MODE" in
  server)
    echo "Starting WoeidChat Server..."
    python woeidchat_server.py
    ;;
  client)
    echo "Starting WoeidChat Client..."
    python woeidchat_client.py
    ;;
  both)
    echo "Starting WoeidChat Server and Client..."
    python woeidchat_server.py &
    sleep 2
    python woeidchat_client.py
    ;;
  *)
    echo "Usage: bash start.sh [server|client|both]"
    exit 1
    ;;
esac
