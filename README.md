# Twilio RIVA Voice Agent

AI-powered voice agent for real estate interactions using NVIDIA RIVA, Twilio, and OpenAI.

## 🚀 Features

- **Real-time Speech Recognition** - NVIDIA RIVA ASR for accurate speech-to-text
- **Natural Voice Synthesis** - RIVA TTS for human-like responses
- **Intelligent Conversations** - OpenAI GPT integration for context-aware dialogue
- **Phone Integration** - Twilio for handling phone calls
- **GPU Acceleration** - Optimized for NVIDIA A10G GPU
- **Monitoring Dashboard** - Real-time health checks and metrics

## 📋 Requirements

- AWS g5.2xlarge instance (or equivalent with NVIDIA GPU)
- Ubuntu 24.04 LTS
- Python 3.12+
- NVIDIA Driver 580+
- CUDA 12.6+
- Docker 28.4+

## 🛠️ Installation

1. Clone the repository:
```bash
git clone https://github.com/AllDayAutomationsai/twilio-riva-agent.git
cd twilio-riva-agent
```

2. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your credentials
```

5. Start the service:
```bash
./deploy.sh start
```

## 📞 Usage

Once running, the system handles incoming calls to your configured Twilio phone number.

### Monitoring
- Health endpoint: `http://localhost:9090/health`
- Metrics: `http://localhost:9090/metrics`
- Dashboard: `http://localhost:8501` (if enabled)

### Service Management
```bash
# Start service
sudo systemctl start twilio-riva-agent

# Stop service  
sudo systemctl stop twilio-riva-agent

# Check status
sudo systemctl status twilio-riva-agent

# View logs
journalctl -u twilio-riva-agent -f
```

## 🏗️ Architecture

```
Phone Call → Twilio → WebSocket → RIVA ASR → OpenAI GPT → RIVA TTS → Audio Stream
```

## 📁 Project Structure

```
twilio_riva_agent/
├── main.py                 # Main WebSocket server
├── twiml_server.py         # Twilio webhook handler
├── monitoring_server.py    # Health monitoring
├── services/
│   ├── riva_asr_client.py # Speech recognition
│   ├── riva_tts_client.py # Text-to-speech
│   ├── openai_client.py   # AI conversation
│   └── websocket_server.py # WebSocket handler
├── systemd/
│   ├── start_service.sh   # Service startup script
│   └── stop_service.sh    # Service shutdown script
└── requirements.txt        # Python dependencies
```

## 🔐 Security

- Never commit `.env` files
- Use environment variables for sensitive data
- Regularly update dependencies
- Monitor access logs

## 📈 Recent Updates (2025-09-21)

- Fixed RIVA client API compatibility (v2.22.0)
- Improved service management with retry logic
- Added monitoring and dashboard capabilities
- Enhanced error handling and logging
- Updated all system packages

## 📝 License

Proprietary - All Day Automations AI

## 🤝 Support

For issues or questions, contact: admin@alldayautomations.ai
