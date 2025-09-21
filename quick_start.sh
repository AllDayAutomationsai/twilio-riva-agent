#!/bin/bash

echo "===================================="
echo "Starting Twilio RIVA Voice Agent"
echo "===================================="

# Kill existing processes
pkill -f "ngrok" 2>/dev/null
pkill -f "python3.*main.py" 2>/dev/null
pkill -f "python3.*twiml_server.py" 2>/dev/null

cd /home/ubuntu/twilio_riva_agent

# Start ngrok in background for WebSocket
echo "Starting ngrok for WebSocket (port 8080)..."
nohup ngrok http 8080 > /home/ubuntu/twilio_riva_agent/logs/ngrok_ws.log 2>&1 &
NGROK_PID=$!
echo "Ngrok WebSocket PID: $NGROK_PID"

# Wait for ngrok to initialize
sleep 5

# Get ngrok URL
echo "Getting ngrok public URL..."
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for tunnel in data['tunnels']:
        if tunnel['proto'] == 'https':
            print(tunnel['public_url'])
            break
except:
    pass
")

if [ -z "$NGROK_URL" ]; then
    echo "ERROR: Could not get ngrok URL. Trying alternative method..."
    
    # Alternative: Just run services locally without ngrok for now
    echo "Running services locally (no public URL)"
    WEBSOCKET_URL="ws://localhost:8080"
    TWIML_URL="http://localhost:5000"
else
    WEBSOCKET_URL=$(echo $NGROK_URL | sed 's/https:/wss:/g')
    TWIML_URL="$NGROK_URL"
    echo "✓ WebSocket URL: $WEBSOCKET_URL"
fi

# Update environment
export WEBSOCKET_URL=$WEBSOCKET_URL
export TWIML_PORT=5000

# Start the main voice agent
echo "Starting Voice Agent..."
nohup python3 /home/ubuntu/twilio_riva_agent/main.py > /home/ubuntu/twilio_riva_agent/logs/voice_agent.log 2>&1 &
AGENT_PID=$!
echo "Voice Agent PID: $AGENT_PID"

# Start TwiML server
echo "Starting TwiML server..."
nohup python3 /home/ubuntu/twilio_riva_agent/twiml_server.py > /home/ubuntu/twilio_riva_agent/logs/twiml_server.log 2>&1 &
TWIML_PID=$!
echo "TwiML Server PID: $TWIML_PID"

sleep 3

echo ""
echo "===================================="
echo "✅ Services Started!"
echo "===================================="
echo ""

if [ ! -z "$NGROK_URL" ]; then
    echo "📞 CONFIGURE TWILIO:"
    echo "   Set your phone number webhook to:"
    echo "   $NGROK_URL/voice"
else
    echo "⚠️  Running locally only (no public URL)"
    echo "   You need to set up ngrok or use a public server"
fi

echo ""
echo "📝 Process PIDs:"
echo "   Voice Agent: $AGENT_PID"
echo "   TwiML Server: $TWIML_PID"
echo "   Ngrok: $NGROK_PID"
echo ""
echo "📂 Check logs:"
echo "   tail -f /home/ubuntu/twilio_riva_agent/logs/voice_agent.log"
echo "   tail -f /home/ubuntu/twilio_riva_agent/logs/twiml_server.log"
echo ""
echo "To stop all services:"
echo "   pkill -f ngrok"
echo "   pkill -f python3"
echo "===================================="
