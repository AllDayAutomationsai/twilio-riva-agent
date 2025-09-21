#!/bin/bash

# Load environment variables
source /home/ubuntu/twilio_riva_agent/.env

# Kill any existing processes
pkill -f "python3.*main.py"
pkill -f "python3.*twiml_server.py"
pkill -f ngrok

echo "Starting Twilio RIVA Voice Agent..."

# Start ngrok for WebSocket (port 8080)
echo "Starting ngrok for WebSocket server..."
ngrok http 8080 --log stdout > /home/ubuntu/twilio_riva_agent/logs/ngrok_ws.log 2>&1 &
NGROK_WS_PID=$!

# Start ngrok for TwiML server (port 5000)
echo "Starting ngrok for TwiML server..."
ngrok http 5000 --log stdout > /home/ubuntu/twilio_riva_agent/logs/ngrok_twiml.log 2>&1 &
NGROK_TWIML_PID=$!

# Wait for ngrok to start
sleep 5

# Get ngrok public URLs
echo "Getting ngrok public URLs..."
WEBSOCKET_PUBLIC_URL=$(curl -s http://localhost:4040/api/tunnels | python3 -c "import sys, json; data = json.load(sys.stdin); print([t['public_url'] for t in data['tunnels'] if '8080' in t['config']['addr']][0].replace('https://', 'wss://'))" 2>/dev/null || echo "")
TWIML_PUBLIC_URL=$(curl -s http://localhost:4040/api/tunnels | python3 -c "import sys, json; data = json.load(sys.stdin); print([t['public_url'] for t in data['tunnels'] if '5000' in t['config']['addr']][0])" 2>/dev/null || echo "")

if [ -z "$WEBSOCKET_PUBLIC_URL" ] || [ -z "$TWIML_PUBLIC_URL" ]; then
    echo "Failed to get ngrok URLs. Please check ngrok installation and try again."
    exit 1
fi

echo "WebSocket URL: $WEBSOCKET_PUBLIC_URL"
echo "TwiML URL: $TWIML_PUBLIC_URL/voice"

# Update .env with public URLs
echo "WEBSOCKET_URL=$WEBSOCKET_PUBLIC_URL" >> /home/ubuntu/twilio_riva_agent/.env
echo "TWIML_URL=$TWIML_PUBLIC_URL" >> /home/ubuntu/twilio_riva_agent/.env

# Start the main voice agent
echo "Starting Voice Agent..."
cd /home/ubuntu/twilio_riva_agent
python3 main.py > /home/ubuntu/twilio_riva_agent/logs/voice_agent.log 2>&1 &
AGENT_PID=$!

# Start the TwiML server
echo "Starting TwiML server..."
python3 twiml_server.py > /home/ubuntu/twilio_riva_agent/logs/twiml_server.log 2>&1 &
TWIML_PID=$!

echo "==============================================="
echo "Twilio RIVA Voice Agent is running!"
echo "==============================================="
echo "WebSocket URL: $WEBSOCKET_PUBLIC_URL"
echo "TwiML Webhook URL: $TWIML_PUBLIC_URL/voice"
echo ""
echo "Configure your Twilio phone number with:"
echo "Voice webhook: $TWIML_PUBLIC_URL/voice"
echo ""
echo "Process PIDs:"
echo "  Voice Agent: $AGENT_PID"
echo "  TwiML Server: $TWIML_PID"
echo "  Ngrok WS: $NGROK_WS_PID"
echo "  Ngrok TwiML: $NGROK_TWIML_PID"
echo ""
echo "Logs:"
echo "  Voice Agent: /home/ubuntu/twilio_riva_agent/logs/voice_agent.log"
echo "  TwiML Server: /home/ubuntu/twilio_riva_agent/logs/twiml_server.log"
echo "  Ngrok WS: /home/ubuntu/twilio_riva_agent/logs/ngrok_ws.log"
echo "  Ngrok TwiML: /home/ubuntu/twilio_riva_agent/logs/ngrok_twiml.log"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for interrupt
trap "echo 'Stopping all services...'; kill $AGENT_PID $TWIML_PID $NGROK_WS_PID $NGROK_TWIML_PID; exit" INT
wait
