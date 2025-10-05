#!/bin/bash
while true; do
    # Check main.py
    if ! pgrep -f "python.*main.py" > /dev/null; then
        echo "[$(date)] Restarting main.py..."
        cd /home/ubuntu/twilio_riva_agent
        source venv/bin/activate
        nohup python main.py > logs/voice_agent.log 2>&1 &
    fi
    
    # Check twiml_server.py
    if ! pgrep -f "python.*twiml_server.py" > /dev/null; then
        echo "[$(date)] Restarting twiml_server.py..."
        cd /home/ubuntu/twilio_riva_agent
        source venv/bin/activate
        WEBSOCKET_URL=wss://burst-news-populations-products.trycloudflare.com nohup python twiml_server.py > logs/twiml_server.log 2>&1 &
    fi
    
    # Check cloudflared for TwiML
    if [ $(pgrep -f "cloudflared.*5000" | wc -l) -eq 0 ]; then
        echo "[$(date)] Restarting cloudflared for TwiML..."
        nohup cloudflared tunnel --url http://localhost:5000 > /home/ubuntu/twilio_riva_agent/logs/cloudflare_twiml.log 2>&1 &
    fi
    
    # Check cloudflared for WebSocket  
    if [ $(pgrep -f "cloudflared.*8080" | wc -l) -eq 0 ]; then
        echo "[$(date)] Restarting cloudflared for WebSocket..."
        nohup cloudflared tunnel --url http://localhost:8080 > /home/ubuntu/twilio_riva_agent/logs/cloudflare_ws.log 2>&1 &
    fi
    
    sleep 10
done
