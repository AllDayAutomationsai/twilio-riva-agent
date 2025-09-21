#!/bin/bash

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║           TWILIO RIVA VOICE AGENT STATUS                  ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check services
VOICE_AGENT=$(ps aux | grep "python3.*main.py" | grep -v grep | wc -l)
TWIML_SERVER=$(ps aux | grep "python3.*twiml_server.py" | grep -v grep | wc -l)
CLOUDFLARE=$(ps aux | grep cloudflared | grep -v grep | wc -l)

echo "🔹 Service Status:"
if [ $VOICE_AGENT -gt 0 ]; then
    echo "   ✅ Voice Agent: Running"
else
    echo "   ❌ Voice Agent: Stopped"
fi

if [ $TWIML_SERVER -gt 0 ]; then
    echo "   ✅ TwiML Server: Running"
else
    echo "   ❌ TwiML Server: Stopped"
fi

if [ $CLOUDFLARE -gt 0 ]; then
    echo "   ✅ Cloudflare Tunnels: Running ($CLOUDFLARE tunnels)"
else
    echo "   ❌ Cloudflare Tunnels: Not running"
fi

echo ""
echo "🔹 Configuration:"
echo "   📞 Twilio Phone: +17542542410"
echo "   🤖 AI Model: OpenAI GPT-4o-mini"
echo "   🎙️ ASR/TTS: NVIDIA RIVA (localhost:50051)"

echo ""
echo "🔹 Public URLs:"
echo "   Webhook: https://automatically-add-britain-chronicles.trycloudflare.com/voice"
echo "   WebSocket: wss://recorders-wild-queensland-adam.trycloudflare.com"

echo ""
echo "🔹 Quick Commands:"
echo "   View logs: tail -f /home/ubuntu/twilio_riva_agent/logs/*.log"
echo "   Test call: Call +17542542410"
echo "   Stop all: pkill -f python3 && pkill -f cloudflared"
echo ""
echo "═══════════════════════════════════════════════════════════"
