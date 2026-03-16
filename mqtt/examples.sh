#!/usr/bin/env bash
# Example MQTT commands for the Wiz bulb
# Run these with: ./send_mqtt.sh '<payload>'
#
# IMPORTANT: userConfigTs and favConfigTs must be incremented
# each time you send the respective command. Query current value
# first with the UDP tool:
#   python3 tools/wiz_udp.py get-user-config

SEND="./send_mqtt.sh"

echo "=== Set fade in/out to 700ms ==="
echo "$SEND" ''\''{"method":"setUserConfig","params":{"fadeIn":700,"fadeOut":700,"dftDim":100,"po":false,"userConfigTs":2}}'\'''
echo ""

echo "=== Set fade in/out to 0 (instant, like stock) ==="
echo "$SEND" ''\''{"method":"setUserConfig","params":{"fadeIn":0,"fadeOut":0,"dftDim":100,"po":false,"userConfigTs":3}}'\'''
echo ""

echo "=== Set power-on behavior to last state ==="
echo "$SEND" ''\''{"method":"setUserConfig","params":{"fadeIn":700,"fadeOut":700,"dftDim":100,"po":true,"userConfigTs":4}}'\'''
echo ""

echo "=== Set WizClick favorites ==="
echo "Favs array: [sceneId, r, g, b, warmWhite, coolWhite, colorTemp]"
echo "Opts array: per-favorite options like {\"dim\":50}"
echo "$SEND" ''\''{"method":"setFavs","params":{"favs":[[12,0,0,0,0,0,0],[11,0,0,0,0,0,0],[6,0,0,0,0,0,0],[0,0,0,0,0,0,3000]],"opts":[{},{},{},{"dim":50}],"favConfigTs":2}}'\'''
echo ""

echo "=== Set favorite 1 to warm 3000K at 80% ==="
echo "$SEND" ''\''{"method":"setFavs","params":{"favs":[[0,0,0,0,0,0,3000],[11,0,0,0,0,0,0],[6,0,0,0,0,0,0],[2,0,0,0,0,0,0]],"opts":[{"dim":80},{},{},{}],"favConfigTs":3}}'\'''
echo ""

echo "=== Trigger OTA firmware update ==="
echo "WARNING: This will attempt to download firmware from firmware.wiz.world"
echo "         Make sure you control DNS/HTTP if you want to serve custom firmware"
echo "$SEND" ''\''{"method":"updateOta","params":{"fw":"1.36.1","s1":"HASH_HERE","s2":"HASH_HERE"}}'\'''
