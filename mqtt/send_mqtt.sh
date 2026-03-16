#!/usr/bin/env bash
# Send an MQTT command to the Wiz bulb via local Mosquitto
# Usage: ./send_mqtt.sh '{"method":"setUserConfig","params":{...}}'
set -euo pipefail

MQTT_HOST="${MQTT_HOST:-localhost}"
MQTT_PORT="${MQTT_PORT:-8883}"
HOME_ID="19223990"
MAC="444f8e3136ba"
TOPIC="OP/pro/${HOME_ID}/devices/${MAC}"
CERT_DIR="$(dirname "$0")/certs"

if [ $# -lt 1 ]; then
  echo "Usage: $0 '<json_payload>'"
  echo "Example: $0 '{\"method\":\"getUserConfig\",\"params\":{}}'"
  exit 1
fi

echo "Publishing to ${TOPIC}:"
echo "$1" | python3 -m json.tool 2>/dev/null || echo "$1"
echo ""

mosquitto_pub \
  --cafile "$CERT_DIR/ca.crt" \
  --insecure \
  -h "$MQTT_HOST" \
  -p "$MQTT_PORT" \
  -t "$TOPIC" \
  -m "$1"

echo "Sent."
