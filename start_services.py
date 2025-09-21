#!/usr/bin/env python3
"""
Start all services for the Twilio RIVA Voice Agent
"""
import subprocess
import time
import json
import requests
import sys
import os
import signal
from dotenv import load_dotenv

load_dotenv()

def start_ngrok_tunnel(port, name):
    """Start an ngrok tunnel for a specific port"""
    print(f"Starting ngrok for {name} on port {port}...")
    process = subprocess.Popen(
        ['ngrok', 'http', str(port), '--log', 'stdout'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    return process

def get_ngrok_url(port, retries=10):
    """Get the public URL from ngrok API"""
    for i in range(retries):
        try:
            response = requests.get('http://localhost:4040/api/tunnels')
            tunnels = response.json()['tunnels']
            for tunnel in tunnels:
                if str(port) in tunnel['config']['addr']:
                    return tunnel['public_url']
        except:
            time.sleep(1)
    return None

def update_env_file(websocket_url, twiml_url):
    """Update the .env file with public URLs"""
    env_file = '/home/ubuntu/twilio_riva_agent/.env'
    
    # Read existing env
    with open(env_file, 'r') as f:
        lines = f.readlines()
    
    # Filter out old URLs
    lines = [l for l in lines if not l.startswith('WEBSOCKET_URL=') and not l.startswith('TWIML_URL=')]
    
    # Add new URLs
    lines.append(f'WEBSOCKET_URL={websocket_url}\n')
    lines.append(f'TWIML_URL={twiml_url}\n')
    
    # Write back
    with open(env_file, 'w') as f:
        f.writelines(lines)

def main():
    print("=" * 50)
    print("Starting Twilio RIVA Voice Agent")
    print("=" * 50)
    
    # Kill any existing processes
    subprocess.run(['pkill', '-f', 'python3.*main.py'], capture_output=True)
    subprocess.run(['pkill', '-f', 'python3.*twiml_server.py'], capture_output=True)
    subprocess.run(['pkill', '-f', 'ngrok'], capture_output=True)
    time.sleep(2)
    
    # Start ngrok tunnels
    ngrok_ws = start_ngrok_tunnel(8080, "WebSocket")
    time.sleep(2)
    ngrok_twiml = start_ngrok_tunnel(5000, "TwiML")
    time.sleep(3)
    
    # Get public URLs
    print("\nGetting ngrok public URLs...")
    ws_url = get_ngrok_url(8080)
    twiml_url = get_ngrok_url(5000)
    
    if not ws_url or not twiml_url:
        print("ERROR: Failed to get ngrok URLs")
        print("Please ensure ngrok is installed correctly")
        sys.exit(1)
    
    # Convert https to wss for WebSocket
    ws_url_wss = ws_url.replace('https://', 'wss://')
    
    print(f"\n✓ WebSocket URL: {ws_url_wss}")
    print(f"✓ TwiML URL: {twiml_url}")
    
    # Update environment
    update_env_file(ws_url_wss, twiml_url)
    os.environ['WEBSOCKET_URL'] = ws_url_wss
    os.environ['TWIML_URL'] = twiml_url
    
    # Start the main voice agent
    print("\nStarting Voice Agent...")
    voice_agent = subprocess.Popen(
        ['python3', '/home/ubuntu/twilio_riva_agent/main.py'],
        stdout=open('/home/ubuntu/twilio_riva_agent/logs/voice_agent.log', 'w'),
        stderr=subprocess.STDOUT
    )
    
    # Start the TwiML server
    print("Starting TwiML server...")
    twiml_server = subprocess.Popen(
        ['python3', '/home/ubuntu/twilio_riva_agent/twiml_server.py'],
        stdout=open('/home/ubuntu/twilio_riva_agent/logs/twiml_server.log', 'w'),
        stderr=subprocess.STDOUT,
        env={**os.environ, 'WEBSOCKET_URL': ws_url_wss}
    )
    
    time.sleep(2)
    
    print("\n" + "=" * 50)
    print("✅ Twilio RIVA Voice Agent is running!")
    print("=" * 50)
    print(f"\n📞 CONFIGURE YOUR TWILIO PHONE NUMBER:")
    print(f"   Voice Webhook URL: {twiml_url}/voice")
    print(f"   Method: POST")
    print("\n🔗 Service URLs:")
    print(f"   WebSocket: {ws_url_wss}")
    print(f"   TwiML: {twiml_url}/voice")
    print("\n📝 Process PIDs:")
    print(f"   Voice Agent: {voice_agent.pid}")
    print(f"   TwiML Server: {twiml_server.pid}")
    print(f"   Ngrok WS: {ngrok_ws.pid}")
    print(f"   Ngrok TwiML: {ngrok_twiml.pid}")
    print("\n📂 Logs:")
    print("   Voice Agent: /home/ubuntu/twilio_riva_agent/logs/voice_agent.log")
    print("   TwiML Server: /home/ubuntu/twilio_riva_agent/logs/twiml_server.log")
    print("\nPress Ctrl+C to stop all services")
    print("=" * 50)
    
    # Handle shutdown
    def signal_handler(sig, frame):
        print("\n\nStopping all services...")
        voice_agent.terminate()
        twiml_server.terminate()
        ngrok_ws.terminate()
        ngrok_twiml.terminate()
        subprocess.run(['pkill', '-f', 'ngrok'], capture_output=True)
        print("All services stopped.")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Wait forever
    try:
        voice_agent.wait()
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == '__main__':
    main()
