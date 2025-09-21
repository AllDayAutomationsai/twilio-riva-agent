# Twilio RIVA Voice Agent - Deployment Guide

## Table of Contents
1. [System Requirements](#system-requirements)
2. [Pre-Deployment Checklist](#pre-deployment-checklist)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Deployment](#deployment)
6. [Performance Optimization](#performance-optimization)
7. [Monitoring & Maintenance](#monitoring--maintenance)
8. [Troubleshooting](#troubleshooting)
9. [Security Considerations](#security-considerations)
10. [Backup & Recovery](#backup--recovery)

## System Requirements

### Hardware Requirements
- **CPU**: Minimum 4 cores, recommended 8 cores (for GPU server: NVIDIA GPU required for RIVA)
- **RAM**: Minimum 8GB, recommended 16GB
- **Storage**: Minimum 50GB SSD
- **Network**: Stable internet connection with low latency

### Software Requirements
- **OS**: Ubuntu 20.04 LTS or higher
- **Python**: 3.8 or higher
- **Docker**: 20.10 or higher (for RIVA services)
- **Node.js**: 16.x or higher
- **NVIDIA Driver**: 470 or higher (for GPU servers)
- **CUDA**: 11.4 or higher (for GPU servers)

### Service Dependencies
- NVIDIA RIVA Server (for ASR/TTS)
- Twilio Account with Voice capabilities
- OpenAI API access
- ngrok Pro account (for production)

## Pre-Deployment Checklist

### Credentials Required
- [ ] Twilio Account SID
- [ ] Twilio Auth Token
- [ ] Twilio Phone Number
- [ ] OpenAI API Key
- [ ] ngrok Auth Token (optional but recommended)
- [ ] Cloudflare credentials (if using Cloudflare tunnel)

### Network Configuration
- [ ] Ports 5000 (TwiML), 8080 (WebSocket), 9090 (Monitoring) accessible
- [ ] Firewall rules configured
- [ ] SSL certificates (for production)
- [ ] Domain names configured (optional)

## Installation

### Quick Install
```bash
# Clone the repository
cd /home/ubuntu
git clone https://github.com/yourusername/twilio_riva_agent.git
cd twilio_riva_agent

# Run deployment script
./deploy.sh install
```

### Manual Installation

#### 1. Install System Dependencies
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install -y python3 python3-pip python3-venv

# Install Node.js and npm
sudo apt install -y nodejs npm

# Install Docker (for RIVA)
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER

# Install ngrok
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update && sudo apt install ngrok
```

#### 2. Setup Python Environment
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install psutil pyyaml  # Additional packages for monitoring
```

#### 3. Install RIVA (on GPU server)
```bash
# Pull RIVA containers
docker pull nvcr.io/nvidia/riva/riva-speech:2.13.1

# Download RIVA quickstart
ngc registry resource download-version nvidia/riva/riva_quickstart:2.13.1
cd riva_quickstart_v2.13.1

# Configure and start RIVA
bash riva_init.sh
bash riva_start.sh
```

## Configuration

### Environment Variables
Create `.env` file with your credentials:
```bash
# Twilio Configuration
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890
TWIML_APP_SID=your_app_sid

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini

# RIVA Configuration
RIVA_SERVER_URL=localhost:50051

# ngrok Configuration (optional)
NGROK_AUTHTOKEN=your_ngrok_token

# Cloudflare Configuration (optional)
CLOUDFLARE_EMAIL=your_email
CLOUDFLARE_API_KEY=your_api_key
CLOUDFLARE_ZONE_ID=your_zone_id

# Monitoring
MONITORING_PORT=9090
ENABLE_METRICS=true
```

### RIVA Configuration
Edit `config/riva_optimized.yaml` for performance tuning:
```yaml
# Key settings to adjust
asr:
  chunk_duration_ms: 100  # Lower for better latency
  buffer_size_ms: 200
  
tts:
  chunk_duration_ms: 50
  quality_level: "balanced"  # fast, balanced, or high_quality
```

## Deployment

### Using Systemd Service

#### Install Service
```bash
# Install and enable service
sudo cp systemd/twilio-riva-agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable twilio-riva-agent
```

#### Service Management
```bash
# Start service
sudo systemctl start twilio-riva-agent

# Stop service
sudo systemctl stop twilio-riva-agent

# Restart service
sudo systemctl restart twilio-riva-agent

# Check status
sudo systemctl status twilio-riva-agent

# View logs
sudo journalctl -u twilio-riva-agent -f
```

### Manual Deployment

#### Start All Services
```bash
# Using start script
./start_services.py

# Or using quick start
./quick_start.sh
```

#### Stop All Services
```bash
# Find and kill processes
pkill -f "python main.py"
pkill -f "python twiml_server.py"
pkill -f "ngrok"
```

### Production Deployment with ngrok Pro

```bash
# Configure ngrok
ngrok config add-authtoken YOUR_AUTH_TOKEN

# Start multiple tunnels
./ngrok_pro_setup.sh

# Get public URLs
curl http://localhost:4040/api/tunnels
```

## Performance Optimization

### System Tuning

#### 1. Increase File Descriptors
```bash
# Edit limits.conf
sudo vi /etc/security/limits.conf

# Add:
* soft nofile 65536
* hard nofile 65536
```

#### 2. TCP Tuning
```bash
# Edit sysctl.conf
sudo vi /etc/sysctl.conf

# Add:
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.ipv4.tcp_rmem = 4096 87380 134217728
net.ipv4.tcp_wmem = 4096 65536 134217728

# Apply changes
sudo sysctl -p
```

### Application Optimization

#### 1. Enable Performance Features
```python
# In main.py, enable optimization
from performance_optimizer import PerformanceOptimizer

optimizer = PerformanceOptimizer()
optimizer.initialize()
```

#### 2. Configure Connection Pooling
```python
# Set in config
connection_pool:
  max_size: 10
  min_size: 2
  keepalive_time_ms: 30000
```

#### 3. Enable Caching
```python
cache_manager.set("common_response", response_data)
```

### Load Testing

Run load tests to validate performance:
```bash
# Concurrent calls test
./load_test.py --test-type concurrent --calls 20 --duration 60

# Ramp-up test
./load_test.py --test-type ramp --calls 50 --duration 120

# Spike test
./load_test.py --test-type spike --calls 100
```

## Monitoring & Maintenance

### Health Checks

Access health endpoint:
```bash
curl http://localhost:9090/health
```

### Metrics Collection

#### Prometheus Metrics
```bash
curl http://localhost:9090/metrics
```

#### Dashboard Access
```bash
# Real-time dashboard
http://localhost:3000

# Or via ngrok URL
https://dashboard-xxxxx.ngrok.io
```

### Log Management

#### View Logs
```bash
# Application logs
tail -f logs/voice_agent.log

# Error logs
tail -f logs/errors.log

# Service logs
sudo journalctl -u twilio-riva-agent -f
```

#### Log Rotation
```bash
# Create logrotate config
sudo vi /etc/logrotate.d/twilio-riva-agent

# Add:
/home/ubuntu/twilio_riva_agent/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
```

### Alerting

Configure alerts in `monitoring.py`:
```python
alert_rules = [
    {
        'name': 'high_latency',
        'condition': lambda stats: stats['latency']['p95'] > 1000,
        'severity': 'warning'
    }
]
```

## Troubleshooting

### Common Issues

#### 1. Service Won't Start
```bash
# Check logs
sudo journalctl -u twilio-riva-agent -n 100

# Check port availability
sudo netstat -tlnp | grep -E "5000|8080|9090"

# Verify environment variables
source .env && env | grep TWILIO
```

#### 2. High Latency
```bash
# Check resource usage
htop
nvidia-smi  # For GPU servers

# Check network latency
ping api.openai.com
ping api.twilio.com

# Review performance metrics
curl http://localhost:9090/stats | jq
```

#### 3. RIVA Connection Issues
```bash
# Check RIVA status
docker ps | grep riva

# Test RIVA connection
python -c "import grpc; channel = grpc.insecure_channel('localhost:50051'); print(channel)"

# Restart RIVA
cd riva_quickstart
./riva_stop.sh
./riva_start.sh
```

#### 4. Memory Leaks
```bash
# Monitor memory usage
watch -n 5 "ps aux | grep python | grep -E 'main|twiml'"

# Enable memory profiling
python -m memory_profiler main.py
```

### Debug Mode

Enable debug logging:
```python
# In .env
LOG_LEVEL=DEBUG

# Or in code
logging.basicConfig(level=logging.DEBUG)
```

## Security Considerations

### 1. Secure Credentials
```bash
# Use environment variables, never hardcode
# Encrypt .env file at rest
openssl enc -aes-256-cbc -salt -in .env -out .env.enc

# Decrypt when needed
openssl enc -aes-256-cbc -d -in .env.enc -out .env
```

### 2. Network Security
```bash
# Configure firewall
sudo ufw allow 22/tcp  # SSH
sudo ufw allow 5000/tcp  # TwiML
sudo ufw allow 8080/tcp  # WebSocket
sudo ufw allow 9090/tcp  # Monitoring
sudo ufw enable
```

### 3. SSL/TLS
```bash
# Generate self-signed certificate for testing
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# Use Let's Encrypt for production
sudo apt install certbot
sudo certbot certonly --standalone -d your-domain.com
```

### 4. API Rate Limiting
```python
# Implement rate limiting
from flask_limiter import Limiter

limiter = Limiter(
    app,
    key_func=lambda: request.remote_addr,
    default_limits=["100 per minute"]
)
```

### 5. Input Validation
```python
# Validate all inputs
def validate_phone_number(number):
    import re
    pattern = r'^\+1\d{10}$'
    return re.match(pattern, number) is not None
```

## Backup & Recovery

### Backup Strategy

#### Automated Backups
```bash
# Create backup script
cat > backup.sh << 'SCRIPT'
#!/bin/bash
BACKUP_DIR="/backup/twilio_riva_agent/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# Backup configuration
cp -r config/ $BACKUP_DIR/
cp .env $BACKUP_DIR/

# Backup logs
tar -czf $BACKUP_DIR/logs.tar.gz logs/

# Backup database (if applicable)
# pg_dump dbname > $BACKUP_DIR/database.sql

echo "Backup completed: $BACKUP_DIR"
SCRIPT

# Schedule with cron
crontab -e
# Add: 0 2 * * * /home/ubuntu/twilio_riva_agent/backup.sh
```

### Recovery Procedures

#### Restore from Backup
```bash
# Stop services
sudo systemctl stop twilio-riva-agent

# Restore files
BACKUP_DIR="/backup/twilio_riva_agent/20240101"
cp -r $BACKUP_DIR/config/* config/
cp $BACKUP_DIR/.env .

# Restore logs if needed
tar -xzf $BACKUP_DIR/logs.tar.gz

# Restart services
sudo systemctl start twilio-riva-agent
```

### Disaster Recovery

#### Failover Strategy
1. Set up secondary server with identical configuration
2. Use DNS-based load balancing
3. Configure health checks for automatic failover
4. Maintain real-time replication of critical data

## Performance Benchmarks

### Expected Performance Metrics

| Metric | Target | Acceptable | Critical |
|--------|--------|------------|----------|
| ASR Latency | < 200ms | < 500ms | > 1000ms |
| LLM Response | < 800ms | < 1500ms | > 3000ms |
| TTS Latency | < 150ms | < 300ms | > 500ms |
| End-to-End | < 1500ms | < 2500ms | > 5000ms |
| Success Rate | > 99% | > 95% | < 90% |
| Concurrent Calls | 100 | 50 | < 20 |

### Scaling Guidelines

#### Vertical Scaling
- Increase CPU cores for more concurrent calls
- Add RAM for larger buffers and caches
- Use GPU for faster RIVA processing

#### Horizontal Scaling
- Deploy multiple instances behind load balancer
- Use Redis for shared session storage
- Implement distributed caching

## Support & Resources

### Documentation
- [Twilio Voice API](https://www.twilio.com/docs/voice)
- [NVIDIA RIVA Documentation](https://docs.nvidia.com/deeplearning/riva/)
- [OpenAI API Reference](https://platform.openai.com/docs/)

### Community
- GitHub Issues: https://github.com/yourusername/twilio-riva-agent/issues
- Discord: [Join our server](https://discord.gg/example)

### Professional Support
For enterprise support, contact: support@yourcompany.com

## Version History

### v1.0.0 (Current)
- Initial release with core functionality
- Performance optimization module
- Monitoring and alerting
- Systemd service support
- Load testing capabilities

### Roadmap
- v1.1.0: Multi-language support
- v1.2.0: Advanced analytics dashboard
- v1.3.0: Kubernetes deployment
- v2.0.0: Multi-tenant support

---

Last Updated: 2024-09-21
