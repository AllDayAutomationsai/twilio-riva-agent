#!/usr/bin/env python3
"""
Real-time monitoring dashboard for Twilio RIVA Voice Agent
"""
from aiohttp import web
import aiohttp
import json
import asyncio
import psutil
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Voice Agent Dashboard</title>
    <style>
        body { 
            font-family: 'Segoe UI', Tahoma, sans-serif; 
            margin: 0; 
            padding: 20px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { text-align: center; margin-bottom: 30px; }
        .grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); 
            gap: 20px; 
        }
        .card { 
            background: rgba(255,255,255,0.1); 
            backdrop-filter: blur(10px);
            border-radius: 10px; 
            padding: 20px; 
            border: 1px solid rgba(255,255,255,0.2);
        }
        .card h2 { 
            margin-top: 0; 
            border-bottom: 2px solid rgba(255,255,255,0.3); 
            padding-bottom: 10px;
        }
        .status { 
            display: inline-block; 
            padding: 5px 10px; 
            border-radius: 5px; 
            margin: 5px 0;
            font-weight: bold;
        }
        .status.online { background: #10B981; }
        .status.offline { background: #EF4444; }
        .metric { 
            display: flex; 
            justify-content: space-between; 
            padding: 8px 0; 
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .metric:last-child { border-bottom: none; }
        .logs { 
            background: rgba(0,0,0,0.3); 
            padding: 10px; 
            border-radius: 5px; 
            font-family: monospace;
            font-size: 12px;
            max-height: 200px;
            overflow-y: auto;
        }
        .refresh-btn {
            background: #10B981;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            float: right;
            margin-top: -50px;
        }
        .refresh-btn:hover { background: #059669; }
    </style>
    <script>
        function refreshData() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('status-content').innerHTML = renderStatus(data);
                });
        }
        
        function renderStatus(data) {
            let html = '';
            
            // Services Status
            html += '<div class="card"><h2>🔧 Services</h2>';
            for (const [service, status] of Object.entries(data.services)) {
                html += `<div class="metric">
                    <span>${service}</span>
                    <span class="status ${status ? 'online' : 'offline'}">${status ? 'RUNNING' : 'STOPPED'}</span>
                </div>`;
            }
            html += '</div>';
            
            // System Metrics
            html += '<div class="card"><h2>📊 System Metrics</h2>';
            html += `<div class="metric"><span>CPU Usage</span><span>${data.system.cpu}%</span></div>`;
            html += `<div class="metric"><span>Memory Usage</span><span>${data.system.memory}%</span></div>`;
            html += `<div class="metric"><span>Uptime</span><span>${data.system.uptime}</span></div>`;
            html += '</div>';
            
            // URLs
            html += '<div class="card"><h2>🔗 Endpoints</h2>';
            html += `<div class="metric"><span>Phone</span><span>+17542542410</span></div>`;
            html += `<div class="metric"><span>WebSocket</span><span style="font-size:11px">${data.urls.websocket}</span></div>`;
            html += `<div class="metric"><span>TwiML</span><span style="font-size:11px">${data.urls.twiml}</span></div>`;
            html += '</div>';
            
            // Recent Activity
            html += '<div class="card"><h2>📝 Recent Activity</h2>';
            html += '<div class="logs">';
            data.recent_logs.forEach(log => {
                html += `<div>${log}</div>`;
            });
            html += '</div></div>';
            
            return html;
        }
        
        // Auto-refresh every 5 seconds
        setInterval(refreshData, 5000);
        
        // Initial load
        window.onload = refreshData;
    </script>
</head>
<body>
    <div class="container">
        <h1>🎙️ Twilio RIVA Voice Agent Dashboard</h1>
        <button class="refresh-btn" onclick="refreshData()">↻ Refresh</button>
        <div id="status-content" class="grid">
            <div class="card"><h2>Loading...</h2></div>
        </div>
    </div>
</body>
</html>
"""

async def get_system_status():
    """Get system and service status"""
    status = {
        "services": {},
        "system": {},
        "urls": {},
        "recent_logs": []
    }
    
    # Check services
    import subprocess
    
    # Voice Agent
    result = subprocess.run(['pgrep', '-f', 'python3.*main.py'], capture_output=True)
    status["services"]["Voice Agent"] = result.returncode == 0
    
    # TwiML Server
    result = subprocess.run(['pgrep', '-f', 'python3.*twiml_server.py'], capture_output=True)
    status["services"]["TwiML Server"] = result.returncode == 0
    
    # Ngrok
    result = subprocess.run(['pgrep', '-f', 'ngrok'], capture_output=True)
    status["services"]["Ngrok Tunnels"] = result.returncode == 0
    
    # System metrics
    status["system"]["cpu"] = psutil.cpu_percent(interval=1)
    status["system"]["memory"] = psutil.virtual_memory().percent
    
    # Calculate uptime
    boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
    uptime = datetime.datetime.now() - boot_time
    hours = int(uptime.total_seconds() // 3600)
    minutes = int((uptime.total_seconds() % 3600) // 60)
    status["system"]["uptime"] = f"{hours}h {minutes}m"
    
    # URLs
    status["urls"]["websocket"] = os.getenv("WEBSOCKET_URL", "Not configured")
    status["urls"]["twiml"] = "https://07d591ee897d.ngrok.app/voice"
    
    # Recent logs (last 5 lines)
    try:
        with open('/home/ubuntu/twilio_riva_agent/logs/voice_agent.log', 'r') as f:
            lines = f.readlines()
            status["recent_logs"] = [line.strip() for line in lines[-5:]]
    except:
        status["recent_logs"] = ["No logs available"]
    
    return status

async def handle_index(request):
    """Serve the dashboard HTML"""
    return web.Response(text=HTML_TEMPLATE, content_type='text/html')

async def handle_api_status(request):
    """API endpoint for status data"""
    status = await get_system_status()
    return web.json_response(status)

async def create_app():
    app = web.Application()
    app.router.add_get('/', handle_index)
    app.router.add_get('/api/status', handle_api_status)
    return app

if __name__ == '__main__':
    app = create_app()
    print("Starting dashboard on http://localhost:3000")
    print("Access remotely at: https://dashboard.ngrok.app (configure in ngrok)")
    web.run_app(app, host='0.0.0.0', port=3000)
