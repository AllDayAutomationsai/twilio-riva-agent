#!/usr/bin/env python3
"""
OpenAI GPT-4o-mini client for conversational AI
"""
import asyncio
import logging
import os
from typing import List, Dict, Optional, AsyncGenerator
from openai import AsyncOpenAI
from dotenv import load_dotenv
from collections import defaultdict
import json

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConversationManager:
    def __init__(self, openai_client):
        self.openai_client = openai_client
        self.conversations = defaultdict(list)  # Store conversation history by caller_id
        self.system_prompt = """You are a helpful AI assistant on a phone call. 
        Keep your responses concise and natural for voice conversation.
        Be friendly, professional, and helpful.
        Avoid using markdown, special characters, or formatting that doesn't work well with speech.
        If you need to provide lists, speak them naturally.
        Remember this is a phone conversation, so responses should be conversational."""
        
    async def get_response(self, text: str, caller_id: str, stream: bool = True) -> AsyncGenerator[str, None]:
        """
        Get response from GPT-4o-mini
        
        Args:
            text: User input text
            caller_id: Unique identifier for the caller
            stream: Whether to stream the response
            
        Yields:
            Response text chunks if streaming, otherwise returns complete response
        """
        try:
            # Add user message to conversation history
            self.conversations[caller_id].append({"role": "user", "content": text})
            
            # Prepare messages with system prompt and conversation history
            messages = [
                {"role": "system", "content": self.system_prompt}
            ] + self.conversations[caller_id][-10:]  # Keep last 10 messages for context
            
            # Call OpenAI API
            if stream:
                stream = await self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=150,  # Keep responses concise for voice
                    stream=True
                )
                
                full_response = ""
                async for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        content = chunk.choices[0].delta.content
                        full_response += content
                        yield content
                
                # Add assistant response to history
                self.conversations[caller_id].append({"role": "assistant", "content": full_response})
                
            else:
                response = await self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=150
                )
                
                content = response.choices[0].message.content
                self.conversations[caller_id].append({"role": "assistant", "content": content})
                yield content
                
        except Exception as e:
            logger.error(f"Error getting OpenAI response: {e}")
            yield "I apologize, but I'm having trouble processing that right now."
    
    def clear_conversation(self, caller_id: str):
        """Clear conversation history for a caller"""
        if caller_id in self.conversations:
            del self.conversations[caller_id]
            logger.info(f"Cleared conversation for caller: {caller_id}")
    
    def get_conversation_summary(self, caller_id: str) -> str:
        """Get a summary of the conversation"""
        if caller_id not in self.conversations:
            return "No conversation history"
        
        return json.dumps(self.conversations[caller_id], indent=2)

class OpenAIClient:
    def __init__(self):
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        self.client = AsyncOpenAI(api_key=api_key)
        self.conversation_manager = ConversationManager(self.client)
        logger.info("OpenAI client initialized")
    
    async def process_transcript(self, transcript: str, caller_id: str) -> AsyncGenerator[str, None]:
        """
        Process transcript and get AI response
        
        Args:
            transcript: The user's speech transcript
            caller_id: Unique identifier for the caller
            
        Yields:
            Response text chunks
        """
        logger.info(f"Processing transcript from {caller_id}: {transcript}")
        
        async for chunk in self.conversation_manager.get_response(transcript, caller_id):
            yield chunk
    
    def clear_caller_history(self, caller_id: str):
        """Clear conversation history for a specific caller"""
        self.conversation_manager.clear_conversation(caller_id)

# Response buffer for managing streaming responses
class ResponseBuffer:
    def __init__(self):
        self.buffer = []
        self.complete = False
        
    def add_chunk(self, chunk: str):
        """Add a chunk to the buffer"""
        self.buffer.append(chunk)
    
    def get_complete_sentences(self) -> List[str]:
        """Extract complete sentences from buffer"""
        text = ''.join(self.buffer)
        sentences = []
        
        # Simple sentence detection (can be improved)
        import re
        sentence_endings = re.compile(r'[.!?]\s+')
        parts = sentence_endings.split(text)
        
        if len(parts) > 1:
            # We have at least one complete sentence
            for i in range(len(parts) - 1):
                sentences.append(parts[i] + text[sentence_endings.search(text).group(0)])
            
            # Keep the incomplete part in buffer
            self.buffer = [parts[-1]]
        
        return sentences
    
    def get_remaining(self) -> str:
        """Get any remaining text in buffer"""
        return ''.join(self.buffer)
    
    def clear(self):
        """Clear the buffer"""
        self.buffer = []
        self.complete = False

if __name__ == "__main__":
    # Test the OpenAI client
    async def test():
        try:
            client = OpenAIClient()
            
            # Test conversation
            test_caller = "test_caller_123"
            test_input = "Hello, can you help me with a question?"
            
            response = ""
            async for chunk in client.process_transcript(test_input, test_caller):
                response += chunk
                print(chunk, end="", flush=True)
            
            print(f"\n\nComplete response: {response}")
            
            # Clear history
            client.clear_caller_history(test_caller)
            
        except Exception as e:
            logger.error(f"Test failed: {e}")
    
    asyncio.run(test())
