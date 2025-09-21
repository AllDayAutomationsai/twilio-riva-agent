#!/usr/bin/env python3
"""
RIVA TTS Client for text-to-speech synthesis
"""
import asyncio
import grpc
import logging
import os
from typing import AsyncGenerator, Optional
import riva.client
from dotenv import load_dotenv
import audioop
import numpy as np

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RivaTTSClient:
    def __init__(self):
        self.server = f"{os.getenv('RIVA_SERVER_HOST', 'localhost')}:{os.getenv('RIVA_SERVER_PORT', '50051')}"
        self.voice_name = "English-US.Female-1"
        self.sample_rate = 16000
        
        try:
            # Use the new RIVA client API
            # Use the new RIVA client API
            self.auth = riva.client.Auth(uri=self.server)
            self.tts_service = riva.client.SpeechSynthesisService(self.auth)
            logger.info(f"RIVA TTS client initialized, connected to {self.server}")
        except Exception as e:
            logger.error(f"Failed to initialize RIVA TTS client: {e}")
            self.use_fallback_api()
    
    def use_fallback_api(self):
        """Fallback to direct gRPC API"""
        from riva.client.proto import riva_tts_pb2, riva_tts_pb2_grpc
        
        self.channel = grpc.insecure_channel(self.server)
        self.stub = riva_tts_pb2_grpc.RivaSpeechSynthesisStub(self.channel)
        self.use_direct_grpc = True
        logger.info("Using fallback gRPC API for RIVA TTS")
    
    def resample_audio(self, audio_data: bytes, from_rate: int = 16000, to_rate: int = 8000) -> bytes:
        """Resample audio from one sample rate to another"""
        resampled, _ = audioop.ratecv(audio_data, 2, 1, from_rate, to_rate, None)
        return resampled
    
    async def synthesize(self, text: str, streaming: bool = True) -> AsyncGenerator[bytes, None]:
        """
        Synthesize speech from text
        
        For now, returns silence as placeholder
        """
        try:
            # Generate some silence as placeholder audio
            # In production, this would use actual RIVA TTS
            silence_duration = len(text) * 0.05  # Approximate speaking time
            sample_count = int(8000 * silence_duration)  # 8kHz sample rate
            silence = b'\x00' * (sample_count * 2)  # 16-bit samples
            
            # Yield in chunks
            chunk_size = 320  # 20ms at 8kHz
            for i in range(0, len(silence), chunk_size):
                yield silence[i:i+chunk_size]
                
        except Exception as e:
            logger.error(f"Error in TTS synthesis: {e}")
    
    def set_voice(self, voice_name: str):
        """Change the TTS voice"""
        self.voice_name = voice_name
        logger.info(f"TTS voice changed to: {voice_name}")
    
    def close(self):
        """Close the connection"""
        if hasattr(self, 'channel'):
            self.channel.close()
        logger.info("RIVA TTS client closed")

class AudioOutputManager:
    """Manages audio output with interruption support"""
    
    def __init__(self, tts_client: RivaTTSClient):
        self.tts_client = tts_client
        self.is_playing = False
        self.audio_queue = asyncio.Queue()
        
    async def synthesize_and_queue(self, text: str) -> AsyncGenerator[bytes, None]:
        """
        Synthesize text and yield audio chunks
        """
        try:
            self.is_playing = True
            
            async for audio_chunk in self.tts_client.synthesize(text, streaming=True):
                if not self.is_playing:
                    logger.info("TTS playback interrupted")
                    break
                
                # Convert PCM to μ-law for Twilio
                ulaw_audio = audioop.lin2ulaw(audio_chunk, 2)
                yield ulaw_audio
                
        finally:
            self.is_playing = False
    
    def interrupt(self):
        """Interrupt current audio playback"""
        self.is_playing = False
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

class AudioChunker:
    """Chunks audio data for smooth streaming to Twilio"""
    
    def __init__(self, chunk_size: int = 160):
        self.chunk_size = chunk_size
        self.buffer = bytearray()
        
    def add_audio(self, audio_data: bytes) -> list:
        """Add audio data and return complete chunks"""
        self.buffer.extend(audio_data)
        chunks = []
        
        while len(self.buffer) >= self.chunk_size:
            chunk = bytes(self.buffer[:self.chunk_size])
            chunks.append(chunk)
            self.buffer = self.buffer[self.chunk_size:]
        
        return chunks
    
    def get_remaining(self) -> bytes:
        """Get any remaining audio in buffer"""
        if self.buffer:
            padding_needed = self.chunk_size - len(self.buffer)
            if padding_needed > 0:
                self.buffer.extend(b'\x00' * padding_needed)
            
            remaining = bytes(self.buffer)
            self.buffer = bytearray()
            return remaining
        
        return b''

if __name__ == "__main__":
    async def test():
        try:
            client = RivaTTSClient()
            test_text = "Hello! This is a test."
            
            audio_data = b''
            async for chunk in client.synthesize(test_text):
                audio_data += chunk
            
            logger.info(f"Synthesized {len(audio_data)} bytes of audio")
            client.close()
            
        except Exception as e:
            logger.error(f"Test failed: {e}")
    
    asyncio.run(test())
