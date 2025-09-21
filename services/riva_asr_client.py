#!/usr/bin/env python3
"""
RIVA ASR Client for speech-to-text processing
"""
import asyncio
import grpc
import logging
import numpy as np
from typing import Optional, AsyncGenerator
import riva.client
import os
from dotenv import load_dotenv
import audioop

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RivaASRClient:
    def __init__(self):
        self.server = f"{os.getenv('RIVA_SERVER_HOST', 'localhost')}:{os.getenv('RIVA_SERVER_PORT', '50051')}"
        self.auth = None
        
        try:
            # Use the new RIVA client API
            # Use the new RIVA client API
            self.auth = riva.client.Auth(uri=self.server)
            self.asr_service = riva.client.ASRService(self.auth)
            
            # Configure ASR settings
            self.config = riva.client.StreamingRecognitionConfig(
                config=riva.client.RecognitionConfig(
                    encoding=riva.client.AudioEncoding.LINEAR_PCM,
                    language_code="en-US",
                    sample_rate_hertz=16000,
                    enable_automatic_punctuation=True,
                    max_alternatives=1,
                ),
                interim_results=True,
            )
            
            logger.info(f"RIVA ASR client initialized, connected to {self.server}")
        except Exception as e:
            logger.error(f"Failed to initialize RIVA ASR client: {e}")
            # Fallback to direct gRPC if new API fails
            self.use_fallback_api()
    
    def use_fallback_api(self):
        """Fallback to direct gRPC API if new client fails"""
        from riva.client.proto import riva_asr_pb2, riva_asr_pb2_grpc
        
        self.channel = grpc.insecure_channel(self.server)
        self.stub = riva_asr_pb2_grpc.RivaSpeechRecognitionStub(self.channel)
        
        # Create streaming recognition config
        self.config = riva_asr_pb2.RecognitionConfig(
            encoding=1,  # LINEAR_PCM = 1
            sample_rate_hertz=16000,
            language_code="en-US",
            max_alternatives=1,
            enable_automatic_punctuation=True,
            enable_word_time_offsets=False,
        )
        self.use_direct_grpc = True
        logger.info(f"Using fallback gRPC API for RIVA ASR")
    
    def resample_audio(self, audio_data: bytes, from_rate: int = 8000, to_rate: int = 16000) -> bytes:
        """Resample audio from one sample rate to another"""
        resampled, _ = audioop.ratecv(audio_data, 2, 1, from_rate, to_rate, None)
        return resampled
    
    async def streaming_recognize(self, audio_stream: AsyncGenerator[bytes, None]) -> AsyncGenerator[dict, None]:
        """
        Perform streaming speech recognition
        """
        try:
            # Collect audio chunks for simplified processing
            audio_buffer = []
            async for audio_chunk in audio_stream:
                resampled_audio = self.resample_audio(audio_chunk)
                audio_buffer.append(resampled_audio)
                
                # Process when we have enough audio (e.g., 1 second)
                if len(audio_buffer) >= 50:  # Approximately 1 second at 20ms chunks
                    combined_audio = b''.join(audio_buffer)
                    
                    # For now, yield a placeholder result
                    # In production, this would use actual RIVA streaming
                    yield {
                        'transcript': "[Processing audio...]",
                        'is_final': False,
                        'confidence': 0.0
                    }
                    
                    audio_buffer = []
                    
        except Exception as e:
            logger.error(f"Error in streaming recognition: {e}")
    
    async def recognize_once(self, audio_data: bytes) -> Optional[str]:
        """Perform single utterance recognition"""
        try:
            resampled_audio = self.resample_audio(audio_data)
            
            # For testing, return a placeholder
            return "[Audio received]"
            
        except Exception as e:
            logger.error(f"Error in recognition: {e}")
            return None
    
    def close(self):
        """Close the connection"""
        if hasattr(self, 'channel'):
            self.channel.close()
        logger.info("RIVA ASR client closed")

class AudioProcessor:
    def __init__(self, asr_client: RivaASRClient):
        self.asr_client = asr_client
        self.audio_queue = asyncio.Queue()
        self.is_processing = False
        
    async def add_audio(self, audio_chunk: bytes):
        """Add audio chunk to processing queue"""
        await self.audio_queue.put(audio_chunk)
    
    async def audio_generator(self):
        """Generate audio chunks for ASR"""
        while self.is_processing:
            try:
                audio_chunk = await asyncio.wait_for(self.audio_queue.get(), timeout=0.1)
                yield audio_chunk
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error in audio generator: {e}")
                break
    
    async def start_processing(self, transcript_callback):
        """Start processing audio stream"""
        self.is_processing = True
        
        try:
            async for result in self.asr_client.streaming_recognize(self.audio_generator()):
                await transcript_callback(result)
        except Exception as e:
            logger.error(f"Error in audio processing: {e}")
        finally:
            self.is_processing = False
    
    def stop_processing(self):
        """Stop processing audio"""
        self.is_processing = False

if __name__ == "__main__":
    async def test():
        try:
            client = RivaASRClient()
            logger.info("RIVA ASR client test completed")
            client.close()
        except Exception as e:
            logger.error(f"Test failed: {e}")
    
    asyncio.run(test())
