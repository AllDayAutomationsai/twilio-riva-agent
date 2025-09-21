#!/usr/bin/env python3
"""
WebSocket server for handling Twilio Media Streams
"""
import asyncio
import websockets
import json
import base64
import logging
import audioop
from typing import Dict, Optional
from collections import defaultdict
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TwilioMediaStreamHandler:
    def __init__(self):
        self.connections: Dict[str, dict] = {}
        self.audio_buffers = defaultdict(bytearray)
        self.stream_sids = {}
        self.call_sids = {}
        self.caller_numbers = {}
        
    async def handle_connection(self, websocket, path):
        """Handle new WebSocket connection from Twilio"""
        connection_id = id(websocket)
        logger.info(f"New WebSocket connection: {connection_id}")
        
        try:
            async for message in websocket:
                await self.process_message(websocket, message, connection_id)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Connection closed: {connection_id}")
        finally:
            await self.cleanup_connection(connection_id)
    
    async def process_message(self, websocket, message: str, connection_id: int):
        """Process incoming message from Twilio"""
        try:
            data = json.loads(message)
            event = data.get('event')
            
            if event == 'start':
                await self.handle_start(data, connection_id)
            elif event == 'media':
                await self.handle_media(data, connection_id, websocket)
            elif event == 'stop':
                await self.handle_stop(data, connection_id)
            elif event == 'mark':
                await self.handle_mark(data, connection_id)
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received: {message[:100]}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    async def handle_start(self, data: dict, connection_id: int):
        """Handle stream start event"""
        start_data = data.get('start', {})
        stream_sid = start_data.get('streamSid')
        call_sid = start_data.get('callSid')
        custom_params = start_data.get('customParameters', {})
        
        # Extract caller information
        caller_number = custom_params.get('from', 'Unknown')
        
        self.stream_sids[connection_id] = stream_sid
        self.call_sids[connection_id] = call_sid
        self.caller_numbers[connection_id] = caller_number
        
        self.connections[connection_id] = {
            'stream_sid': stream_sid,
            'call_sid': call_sid,
            'caller_number': caller_number,
            'start_time': asyncio.get_event_loop().time()
        }
        
        logger.info(f"Stream started - SID: {stream_sid}, Call: {call_sid}, From: {caller_number}")
    
    async def handle_media(self, data: dict, connection_id: int, websocket):
        """Handle incoming audio media"""
        media = data.get('media', {})
        payload = media.get('payload')
        
        if payload:
            # Decode the base64 μ-law audio
            audio_bytes = base64.b64decode(payload)
            
            # Buffer the audio
            self.audio_buffers[connection_id].extend(audio_bytes)
            
            # Process buffered audio when we have enough (e.g., 160 bytes = 20ms at 8kHz)
            if len(self.audio_buffers[connection_id]) >= 160:
                await self.process_audio_chunk(connection_id, websocket)
    
    async def process_audio_chunk(self, connection_id: int, websocket):
        """Process a chunk of audio data"""
        audio_chunk = bytes(self.audio_buffers[connection_id][:160])
        self.audio_buffers[connection_id] = self.audio_buffers[connection_id][160:]
        
        # Convert μ-law to PCM for processing
        pcm_audio = audioop.ulaw2lin(audio_chunk, 2)
        
        # Here we'll integrate with RIVA ASR
        # For now, just log
        if connection_id in self.connections:
            caller = self.caller_numbers.get(connection_id, "Unknown")
            # This is where we'll send audio to ASR service
            
    async def handle_stop(self, data: dict, connection_id: int):
        """Handle stream stop event"""
        logger.info(f"Stream stopped for connection: {connection_id}")
        await self.cleanup_connection(connection_id)
    
    async def handle_mark(self, data: dict, connection_id: int):
        """Handle mark event (used for synchronization)"""
        mark = data.get('mark', {})
        name = mark.get('name')
        logger.debug(f"Mark received: {name} for connection {connection_id}")
    
    async def send_audio_to_twilio(self, websocket, audio_data: bytes, stream_sid: str):
        """Send audio back to Twilio"""
        # Convert PCM to μ-law
        ulaw_audio = audioop.lin2ulaw(audio_data, 2)
        
        # Base64 encode
        encoded_audio = base64.b64encode(ulaw_audio).decode('utf-8')
        
        # Create media message
        message = {
            "event": "media",
            "streamSid": stream_sid,
            "media": {
                "payload": encoded_audio
            }
        }
        
        await websocket.send(json.dumps(message))
    
    async def send_clear_to_twilio(self, websocket, stream_sid: str):
        """Send clear message to stop audio playback"""
        message = {
            "event": "clear",
            "streamSid": stream_sid
        }
        await websocket.send(json.dumps(message))
    
    async def cleanup_connection(self, connection_id: int):
        """Clean up connection resources"""
        if connection_id in self.connections:
            del self.connections[connection_id]
        if connection_id in self.audio_buffers:
            del self.audio_buffers[connection_id]
        if connection_id in self.stream_sids:
            del self.stream_sids[connection_id]
        if connection_id in self.call_sids:
            del self.call_sids[connection_id]
        if connection_id in self.caller_numbers:
            del self.caller_numbers[connection_id]

async def start_server():
    """Start the WebSocket server"""
    handler = TwilioMediaStreamHandler()
    host = os.getenv('WEBSOCKET_HOST', '0.0.0.0')
    port = int(os.getenv('WEBSOCKET_PORT', 8080))
    
    logger.info(f"Starting WebSocket server on {host}:{port}")
    
    async with websockets.serve(handler.handle_connection, host, port):
        logger.info("WebSocket server is running...")
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(start_server())
