#!/usr/bin/env python3
"""
TwiML server to handle incoming Twilio calls
"""
from aiohttp import web
from twilio.twiml.voice_response import VoiceResponse, Stream
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# WebSocket URL - will be replaced with ngrok URL
WEBSOCKET_URL = os.getenv('WEBSOCKET_URL', 'wss://your-ngrok-url.ngrok.io')

async def handle_incoming_call(request):
    """Handle incoming call and return TwiML response"""
    
    # Get call information from request
    form_data = await request.post()
    caller = form_data.get('From', 'Unknown')
    called = form_data.get('To', 'Unknown')
    call_sid = form_data.get('CallSid', 'Unknown')
    
    logger.info(f"Incoming call from {caller} to {called} (SID: {call_sid})")
    
    # Create TwiML response
    response = VoiceResponse()
    
    # Add initial greeting
    response.say("Connecting you to the AI assistant...", voice='alice')
    
    # Start Media Stream to WebSocket
    stream = Stream(url=WEBSOCKET_URL)
    stream.parameter(name='from', value=caller)
    stream.parameter(name='callSid', value=call_sid)
    
    response.append(stream)
    
    # Keep the call alive
    response.pause(length=3600)  # 1 hour max call duration
    
    return web.Response(
        text=str(response),
        content_type='application/xml'
    )

async def health_check(request):
    """Health check endpoint"""
    return web.Response(text="OK", status=200)

async def create_app():
    """Create the aiohttp application"""
    app = web.Application()
    
    # Add routes
    app.router.add_post('/voice', handle_incoming_call)
    app.router.add_get('/health', health_check)
    
    return app

def main():
    """Main entry point"""
    app = create_app()
    port = int(os.getenv('TWIML_PORT', 5000))
    
    logger.info(f"Starting TwiML server on port {port}")
    web.run_app(app, host='0.0.0.0', port=port)

if __name__ == '__main__':
    main()
