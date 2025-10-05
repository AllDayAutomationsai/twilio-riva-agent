#!/usr/bin/env python3
"""
TwiML server to handle incoming Twilio calls with Media Streams
"""
from aiohttp import web
from twilio.twiml.voice_response import VoiceResponse, Start
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# WebSocket URL from environment
WEBSOCKET_URL = os.getenv('WEBSOCKET_URL', 'wss://41a7b1b781a1.ngrok.app')

async def handle_voice(request):
    """Handle incoming voice call from Twilio"""
    # Get call information
    data = await request.post()
    caller = data.get('From', 'Unknown')
    called = data.get('To', 'Unknown')
    call_sid = data.get('CallSid', 'Unknown')
    
    logger.info(f"Incoming call from {caller} to {called} (SID: {call_sid})")
    
    # Create TwiML response with Media Streams
    response = VoiceResponse()
    
    # Start the media stream
    start = Start()
    stream = start.stream(url=WEBSOCKET_URL)
    response.append(start)
    
    # Add greeting after stream starts
    response.say("Hello! I'm your AI assistant. How can I help you today?", voice='alice')
    
    # Keep the call alive
    response.pause(length=3600)  # 1 hour max call duration
    
    return web.Response(
        text=str(response),
        content_type='application/xml'
    )

async def health_check(request):
    """Health check endpoint"""
    return web.Response(text='OK')

def create_app():
    """Create the aiohttp application"""
    app = web.Application()
    app.router.add_post('/voice', handle_voice)
    app.router.add_get('/health', health_check)
    return app

if __name__ == '__main__':
    logger.info("Starting TwiML server on port 5000")
    app = create_app()
    web.run_app(app, host='0.0.0.0', port=5000)
