#!/usr/bin/env python3
"""
Main application controller for Twilio RIVA Voice Agent
"""
import asyncio
import websockets
import json
import base64
import logging
import audioop
import sys
import os
from typing import Dict, Optional
from collections import defaultdict
from dotenv import load_dotenv

# Add services directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'services'))

from websocket_server import TwilioMediaStreamHandler
from riva_asr_client import RivaASRClient, AudioProcessor  
from openai_client import OpenAIClient, ResponseBuffer
from riva_tts_client import RivaTTSClient, AudioOutputManager, AudioChunker

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VoiceAgent:
    """Main voice agent orchestrator"""
    
    def __init__(self):
        self.connections: Dict[str, dict] = {}
        self.audio_buffers = defaultdict(bytearray)
        self.stream_sids = {}
        self.call_sids = {}
        self.caller_numbers = {}
        
        # Initialize services
        self.asr_client = RivaASRClient()
        self.openai_client = OpenAIClient()
        self.tts_client = RivaTTSClient()
        
        # Audio processors per connection
        self.audio_processors = {}
        self.output_managers = {}
        self.audio_chunkers = {}
        self.response_buffers = {}
        
        # Track conversation state
        self.is_speaking = defaultdict(bool)
        self.last_transcript = defaultdict(str)
        
        logger.info("Voice Agent initialized")
    
    async def handle_connection(self, websocket, path):
        """Handle new WebSocket connection from Twilio"""
        connection_id = id(websocket)
        logger.info(f"New WebSocket connection: {connection_id}")
        
        # Initialize per-connection resources
        self.audio_processors[connection_id] = AudioProcessor(self.asr_client)
        self.output_managers[connection_id] = AudioOutputManager(self.tts_client)
        self.audio_chunkers[connection_id] = AudioChunker()
        self.response_buffers[connection_id] = ResponseBuffer()
        
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
                await self.handle_start(data, connection_id, websocket)
            elif event == 'media':
                await self.handle_media(data, connection_id, websocket)
            elif event == 'stop':
                await self.handle_stop(data, connection_id)
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received: {message[:100]}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    async def handle_start(self, data: dict, connection_id: int, websocket):
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
            'websocket': websocket,
            'start_time': asyncio.get_event_loop().time()
        }
        
        logger.info(f"Stream started - SID: {stream_sid}, Call: {call_sid}, From: {caller_number}")
        
        # Start ASR processing for this connection
        asyncio.create_task(self.start_asr_processing(connection_id))
        
        # Send initial greeting
        asyncio.create_task(self.send_greeting(connection_id))
    
    async def handle_media(self, data: dict, connection_id: int, websocket):
        """Handle incoming audio media"""
        media = data.get('media', {})
        payload = media.get('payload')
        
        if payload and connection_id in self.audio_processors:
            # Decode the base64 μ-law audio
            audio_bytes = base64.b64decode(payload)
            
            # Convert μ-law to PCM
            pcm_audio = audioop.ulaw2lin(audio_bytes, 2)
            
            # Check if we're currently speaking - if so, check for interruption
            if self.is_speaking[connection_id]:
                # Simple voice activity detection
                # If significant audio detected, interrupt TTS
                audio_level = audioop.rms(pcm_audio, 2)
                if audio_level > 500:  # Threshold for voice detection
                    logger.info(f"Voice detected during TTS, interrupting for connection {connection_id}")
                    self.output_managers[connection_id].interrupt()
                    self.is_speaking[connection_id] = False
            
            # Add to ASR processor
            await self.audio_processors[connection_id].add_audio(pcm_audio)
    
    async def handle_stop(self, data: dict, connection_id: int):
        """Handle stream stop event"""
        logger.info(f"Stream stopped for connection: {connection_id}")
        await self.cleanup_connection(connection_id)
    
    async def start_asr_processing(self, connection_id: int):
        """Start ASR processing for a connection"""
        if connection_id not in self.audio_processors:
            return
        
        async def handle_transcript(result):
            """Handle ASR transcript results"""
            transcript = result['transcript']
            is_final = result['is_final']
            
            if is_final and transcript.strip():
                logger.info(f"Final transcript from {self.caller_numbers.get(connection_id)}: {transcript}")
                
                # Store last transcript
                self.last_transcript[connection_id] = transcript
                
                # Process with OpenAI
                await self.process_with_ai(connection_id, transcript)
        
        # Start processing
        await self.audio_processors[connection_id].start_processing(handle_transcript)
    
    async def process_with_ai(self, connection_id: int, transcript: str):
        """Process transcript with OpenAI and generate response"""
        if connection_id not in self.connections:
            return
        
        caller_id = self.caller_numbers.get(connection_id, "unknown")
        response_buffer = self.response_buffers[connection_id]
        response_buffer.clear()
        
        try:
            # Get AI response
            full_response = ""
            async for chunk in self.openai_client.process_transcript(transcript, caller_id):
                full_response += chunk
                response_buffer.add_chunk(chunk)
                
                # Check for complete sentences to start TTS early
                complete_sentences = response_buffer.get_complete_sentences()
                for sentence in complete_sentences:
                    await self.synthesize_and_send(connection_id, sentence)
            
            # Send any remaining text
            remaining = response_buffer.get_remaining()
            if remaining.strip():
                await self.synthesize_and_send(connection_id, remaining)
                
        except Exception as e:
            logger.error(f"Error processing with AI: {e}")
            await self.synthesize_and_send(connection_id, "I apologize, but I'm having trouble processing that.")
    
    async def synthesize_and_send(self, connection_id: int, text: str):
        """Synthesize text and send audio to Twilio"""
        if connection_id not in self.connections:
            return
        
        websocket = self.connections[connection_id]['websocket']
        stream_sid = self.stream_sids[connection_id]
        output_manager = self.output_managers[connection_id]
        chunker = self.audio_chunkers[connection_id]
        
        try:
            self.is_speaking[connection_id] = True
            
            # Synthesize and send audio
            async for audio_chunk in output_manager.synthesize_and_queue(text):
                if not self.is_speaking[connection_id]:
                    # Interrupted
                    break
                
                # Chunk audio for smooth streaming
                chunks = chunker.add_audio(audio_chunk)
                
                for chunk in chunks:
                    # Base64 encode for Twilio
                    encoded_audio = base64.b64encode(chunk).decode('utf-8')
                    
                    # Create media message
                    message = {
                        "event": "media",
                        "streamSid": stream_sid,
                        "media": {
                            "payload": encoded_audio
                        }
                    }
                    
                    await websocket.send(json.dumps(message))
                    
                    # Small delay for smooth playback
                    await asyncio.sleep(0.02)  # 20ms chunks
            
            # Send any remaining audio
            remaining = chunker.get_remaining()
            if remaining:
                encoded_audio = base64.b64encode(remaining).decode('utf-8')
                message = {
                    "event": "media",
                    "streamSid": stream_sid,
                    "media": {
                        "payload": encoded_audio
                    }
                }
                await websocket.send(json.dumps(message))
                
        except Exception as e:
            logger.error(f"Error in TTS synthesis and sending: {e}")
        finally:
            self.is_speaking[connection_id] = False
    
    async def send_greeting(self, connection_id: int):
        """Send initial greeting to caller"""
        await asyncio.sleep(0.5)  # Small delay for connection establishment
        
        caller = self.caller_numbers.get(connection_id, "")
        greeting = "Hello! I'm your AI assistant. How can I help you today?"
        
        await self.synthesize_and_send(connection_id, greeting)
    
    async def cleanup_connection(self, connection_id: int):
        """Clean up connection resources"""
        # Stop audio processing
        if connection_id in self.audio_processors:
            self.audio_processors[connection_id].stop_processing()
            del self.audio_processors[connection_id]
        
        # Clear conversation history
        caller_id = self.caller_numbers.get(connection_id)
        if caller_id:
            self.openai_client.clear_caller_history(caller_id)
        
        # Clean up other resources
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
        if connection_id in self.output_managers:
            del self.output_managers[connection_id]
        if connection_id in self.audio_chunkers:
            del self.audio_chunkers[connection_id]
        if connection_id in self.response_buffers:
            del self.response_buffers[connection_id]
        if connection_id in self.is_speaking:
            del self.is_speaking[connection_id]
        if connection_id in self.last_transcript:
            del self.last_transcript[connection_id]
        
        logger.info(f"Cleaned up resources for connection {connection_id}")

async def main():
    """Main entry point"""
    try:
        # Create voice agent
        agent = VoiceAgent()
        
        # Start WebSocket server
        host = os.getenv('WEBSOCKET_HOST', '0.0.0.0')
        port = int(os.getenv('WEBSOCKET_PORT', 8080))
        
        logger.info(f"Starting Voice Agent WebSocket server on {host}:{port}")
        
        async with websockets.serve(agent.handle_connection, host, port):
            logger.info("Voice Agent is running...")
            logger.info("Waiting for incoming calls...")
            await asyncio.Future()  # Run forever
            
    except KeyboardInterrupt:
        logger.info("Shutting down Voice Agent...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
