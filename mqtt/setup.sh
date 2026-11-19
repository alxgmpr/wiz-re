#!/usr/bin/env bash
# Set up and run the MQTT intercept broker for Wiz bulbs
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Generate certs if needed
if [ ! -f certs/server.crt ]; then
  echo "==> Generating TLS certificates..."
  bash generate-certs.sh
fi

# Detect local IP
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}')

echo ""
echo "============================================"
echo "  Wiz MQTT Intercept Setup"
echo "============================================"
echo ""
echo "1. Redirect DNS so the bulb connects here."
echo "   Pick ONE method:"
echo ""
echo "   dnsmasq (add to /etc/dnsmasq.conf or /opt/homebrew/etc/dnsmasq.conf):"
echo "     address=/eu.mqtt.wiz.world/${LOCAL_IP}"
echo ""
echo "   /etc/hosts (if bulb uses your machine as DNS):"
echo "     ${LOCAL_IP} eu.mqtt.wiz.world"
echo ""
echo "   Router DNS override:"
echo "     Point eu.mqtt.wiz.world → ${LOCAL_IP}"
echo ""
echo "2. Power-cycle the bulb after DNS change."
echo "   The bulb reconnects to MQTT on boot."
echo ""
echo "3. Watch the Mosquitto logs below for the"
echo "   bulb's connection (client ID: <mac>_<homeId>)"
echo ""
echo "4. Use send_mqtt.sh to publish commands."
echo "   See examples.sh for common commands."
echo ""
echo "============================================"
echo "  Starting Mosquitto on port 8883 (TLS)..."
echo "============================================"
echo ""

mosquitto -c mosquitto.conf -v
