#!/usr/bin/env bash
# Send an MQTT command to a Wiz bulb via local Mosquitto
# Usage: ./send_mqtt.sh <mac> '<json_payload>'
set -euo pipefail

MQTT_HOST="${MQTT_HOST:-localhost}"
MQTT_PORT="${MQTT_PORT:-8883}"
HOME_ID="${HOME_ID:-19223990}"
CERT_DIR="$(dirname "$0")/certs"

if [ $# -lt 2 ]; then
  echo "Usage: $0 <mac> '<json_payload>'"
  echo "Example: $0 444f8e3136ba '{\"method\":\"getUserConfig\",\"params\":{}}'"
  exit 1
fi

MAC="$1"
shift
TOPIC="OP/pro/${HOME_ID}/devices/${MAC}"

PAYLOAD="$1"

echo "Publishing to ${TOPIC}:"
echo "$PAYLOAD" | python3 -m json.tool 2>/dev/null || echo "$PAYLOAD"
echo ""

mosquitto_pub \
  --cafile "$CERT_DIR/ca.crt" \
  --insecure \
  -h "$MQTT_HOST" \
  -p "$MQTT_PORT" \
  -t "$TOPIC" \
  -m "$PAYLOAD"

echo "Sent."
