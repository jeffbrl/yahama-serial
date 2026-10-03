#!/usr/bin/env bash
# ==============================================================================
# Yamaha RX-Z1 MQTT to REST Bridge
# Subscribes to Home Assistant MQTT topics and forwards commands to the REST API.
# ==============================================================================

# Configuration
MQTT_HOST="${MQTT_HOST:-192.168.6.182}"
MQTT_PORT="${MQTT_PORT:-1883}"
MQTT_USER="${MQTT_USER:-mqtt_user}"
MQTT_PASS="${MQTT_PASS:-40356mqtt}"
API_URL="${API_URL:-http://127.0.0.1:8000/api}"

TOPIC_BASE="40356/yamaha_rx_z1"
TOPIC_POWER_SET="${TOPIC_BASE}/power/set"
TOPIC_VOL_SET="${TOPIC_BASE}/volume/set"
TOPIC_VOL_STEP="${TOPIC_BASE}/volume/step"
TOPIC_MUTE_SET="${TOPIC_BASE}/mute/set"
TOPIC_INPUT_SET="${TOPIC_BASE}/input/set"
TOPIC_DSP_SET="${TOPIC_BASE}/dsp/set"

echo "Starting Yamaha MQTT-to-REST bridge..."
echo "Broker: ${MQTT_HOST}:${MQTT_PORT}"
echo "Target API: ${API_URL}"

# Publish status as online (with LWT offline)
mosquitto_pub -h "$MQTT_HOST" -p "$MQTT_PORT" -u "$MQTT_USER" -P "$MQTT_PASS" \
  -t "${TOPIC_BASE}/status" -m "online" -r 2>/dev/null || true

# Continuous listener
mosquitto_sub -h "$MQTT_HOST" -p "$MQTT_PORT" -u "$MQTT_USER" -P "$MQTT_PASS" \
  -t "${TOPIC_BASE}/+/set" -t "${TOPIC_BASE}/volume/step" -v | while read -r topic payload; do
    echo "[MQTT] Received: ${topic} -> ${payload}"

    case "$topic" in
      "${TOPIC_POWER_SET}")
        if [ "$payload" = "ON" ]; then
          curl -s -X POST "${API_URL}/power" -H "Content-Type: application/json" -d '{"power":"ON"}' > /dev/null
          mosquitto_pub -h "$MQTT_HOST" -p "$MQTT_PORT" -u "$MQTT_USER" -P "$MQTT_PASS" -t "${TOPIC_BASE}/power/state" -m "ON" -r
        else
          curl -s -X POST "${API_URL}/power" -H "Content-Type: application/json" -d '{"power":"STANDBY"}' > /dev/null
          mosquitto_pub -h "$MQTT_HOST" -p "$MQTT_PORT" -u "$MQTT_USER" -P "$MQTT_PASS" -t "${TOPIC_BASE}/power/state" -m "OFF" -r
        fi
        ;;

      "${TOPIC_VOL_STEP}")
        if [ "$payload" = "UP" ]; then
          curl -s -X POST "${API_URL}/volume/up" > /dev/null
        elif [ "$payload" = "DOWN" ]; then
          curl -s -X POST "${API_URL}/volume/down" > /dev/null
        fi
        ;;

      "${TOPIC_VOL_SET}")
        # Volume percent integer 0-100
        curl -s -X POST "${API_URL}/volume/percent" -H "Content-Type: application/json" -d "{\"percent\":${payload}}" > /dev/null
        ;;

      "${TOPIC_MUTE_SET}")
        if [ "$payload" = "ON" ]; then
          curl -s -X POST "${API_URL}/mute" -H "Content-Type: application/json" -d '{"mute":true}' > /dev/null
        else
          curl -s -X POST "${API_URL}/mute" -H "Content-Type: application/json" -d '{"mute":false}' > /dev/null
        fi
        ;;

      "${TOPIC_INPUT_SET}")
        curl -s -X POST "${API_URL}/input" -H "Content-Type: application/json" -d "{\"source\":\"${payload}\"}" > /dev/null
        ;;

      "${TOPIC_DSP_SET}")
        curl -s -X POST "${API_URL}/dsp" -H "Content-Type: application/json" -d "{\"dsp\":\"${payload}\"}" > /dev/null
        ;;
    esac
done
