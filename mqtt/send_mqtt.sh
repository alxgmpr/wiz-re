#!/usr/bin/env bash
# Send an MQTT command to a Wiz bulb via local Mosquitto
# Usage: WIZ_MAC=<mac> WIZ_HOME_ID=<homeId> ./send_mqtt.sh '<json_payload>'
set -euo pipefail

MQTT_HOST="${MQTT_HOST:-localhost}"
MQTT_PORT="${MQTT_PORT:-8883}"
CERT_DIR="$(dirname "$0")/certs"

if [ $# -lt 1 ] || [ -z "${WIZ_MAC:-}" ] || [ -z "${WIZ_HOME_ID:-}" ]; then
  echo "Usage: WIZ_MAC=<mac> WIZ_HOME_ID=<homeId> $0 '<json_payload>'"
  echo "Get both from: python3 tools/wiz_udp.py get-system-config"
  exit 1
fi

TOPIC="OP/pro/${WIZ_HOME_ID}/devices/${WIZ_MAC}"
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
