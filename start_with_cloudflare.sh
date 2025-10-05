#!/bin/bash

echo "========================================"
echo "Starting Twilio RIVA Voice Agent"
echo "Using Cloudflare Tunnels"
echo "========================================"

# Load environment variables
source /home/ubuntu/twilio_riva_agent/.env

# Kill any existing processes
pkill -f "python3.*main.py"
pkill -f "python3.*twiml_server.py"
pkill -f "cloudflared"

echo "Starting services..."

# Start Cloudflare tunnel for TwiML server (port 5000)
echo "Starting Cloudflare tunnel for TwiML server (port 5000)..."
cloudflared tunnel --url http://localhost:5000 > /home/ubuntu/twilio_riva_agent/logs/cloudflare_twiml.log 2>&1 &
TWIML_TUNNEL_PID=$!

# Start Cloudflare tunnel for WebSocket server (port 8080)
echo "Starting Cloudflare tunnel for WebSocket server (port 8080)..."
cloudflared tunnel --url http://localhost:8080 > /home/ubuntu/twilio_riva_agent/logs/cloudflare_ws.log 2>&1 &
WS_TUNNEL_PID=$!

# Wait for tunnels to establish
echo "Waiting for Cloudflare tunnels to establish..."
sleep 8

# Extract the public URLs from logs
echo "Getting public URLs..."
TWIML_URL=$(grep -o 'https://.*\.trycloudflare\.com' /home/ubuntu/twilio_riva_agent/logs/cloudflare_twiml.log | head -1)
WS_URL_TEMP=$(grep -o 'https://.*\.trycloudflare\.com' /home/ubuntu/twilio_riva_agent/logs/cloudflare_ws.log | head -1)
WS_URL=$(echo $WS_URL_TEMP | sed 's/https:/wss:/')

if [ -z "$TWIML_URL" ] || [ -z "$WS_URL" ]; then
    echo "Failed to get Cloudflare tunnel URLs. Checking logs..."
    echo "TwiML log:"
    tail -5 /home/ubuntu/twilio_riva_agent/logs/cloudflare_twiml.log
    echo "WebSocket log:"
    tail -5 /home/ubuntu/twilio_riva_agent/logs/cloudflare_ws.log
    exit 1
fi

echo "TwiML URL: $TWIML_URL/voice"
echo "WebSocket URL: $WS_URL"

# Update environment with public URLs
export WEBSOCKET_URL=$WS_URL
export TWIML_URL=$TWIML_URL

# Start the main voice agent
echo "Starting Voice Agent..."
cd /home/ubuntu/twilio_riva_agent
source /home/ubuntu/twilio_riva_agent/venv/bin/activate && python main.py > /home/ubuntu/twilio_riva_agent/logs/voice_agent.log 2>&1 &
AGENT_PID=$!

# Start the TwiML server
echo "Starting TwiML server..."
source /home/ubuntu/twilio_riva_agent/venv/bin/activate && python twiml_server.py > /home/ubuntu/twilio_riva_agent/logs/twiml_server.log 2>&1 &
TWIML_PID=$!

# Save PIDs for later management
echo $AGENT_PID > /home/ubuntu/twilio_riva_agent/pids/voice_agent.pid
echo $TWIML_PID > /home/ubuntu/twilio_riva_agent/pids/twiml_server.pid
echo $TWIML_TUNNEL_PID > /home/ubuntu/twilio_riva_agent/pids/cloudflare_twiml.pid
echo $WS_TUNNEL_PID > /home/ubuntu/twilio_riva_agent/pids/cloudflare_ws.pid

# Wait a moment for services to start
sleep 3

# Update Twilio webhook configuration
echo "Updating Twilio phone number webhook..."
twilio phone-numbers:update +17542542410 \
    --voice-url="${TWIML_URL}/voice" \
    --voice-method=POST

echo ""
echo "========================================"
echo "Services started successfully!"
echo "========================================"
echo "📞 Phone Number: +17542542410"
echo "🔗 TwiML Webhook: ${TWIML_URL}/voice"
echo "🔗 WebSocket URL: ${WS_URL}"
echo ""
echo "To test: Call +17542542410"
echo "To view logs: tail -f /home/ubuntu/twilio_riva_agent/logs/*.log"
echo "To check status: ./status.sh"
echo "========================================"
