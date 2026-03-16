#!/usr/bin/env bash
# Generate self-signed CA + server cert for MQTT interception
# Server cert CN must match the Wiz MQTT hostname
set -euo pipefail

CERT_DIR="$(dirname "$0")/certs"
MQTT_HOST="eu.mqtt.wiz.world"
DAYS=3650

mkdir -p "$CERT_DIR"

echo "==> Generating CA key and certificate..."
openssl genrsa -out "$CERT_DIR/ca.key" 2048
openssl req -new -x509 -days "$DAYS" -key "$CERT_DIR/ca.key" \
  -out "$CERT_DIR/ca.crt" -subj "/CN=WizMQTT-CA"

echo "==> Generating server key and CSR..."
openssl genrsa -out "$CERT_DIR/server.key" 2048
openssl req -new -key "$CERT_DIR/server.key" \
  -out "$CERT_DIR/server.csr" -subj "/CN=${MQTT_HOST}"

echo "==> Signing server certificate with CA..."
# Include SAN for modern TLS validation
openssl x509 -req -in "$CERT_DIR/server.csr" \
  -CA "$CERT_DIR/ca.crt" -CAkey "$CERT_DIR/ca.key" -CAcreateserial \
  -out "$CERT_DIR/server.crt" -days "$DAYS" \
  -extfile <(printf "subjectAltName=DNS:%s" "$MQTT_HOST")

rm -f "$CERT_DIR/server.csr" "$CERT_DIR/ca.srl"

echo "==> Certificates generated in $CERT_DIR/"
ls -la "$CERT_DIR/"
