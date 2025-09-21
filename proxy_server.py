#!/usr/bin/env python3
"""
Proxy server to handle both TwiML and WebSocket through single ngrok tunnel
"""
from aiohttp import web
import aiohttp
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def handle_proxy(request):
    """Proxy requests based on path"""
    path = request.path_qs
    
    # Route based on path
    if path.startswith('/voice'):
        # Forward to TwiML server on port 5000
        target_url = f"http://localhost:5000{path}"
    else:
        # Default to WebSocket server on port 8080
        target_url = f"http://localhost:8080{path}"
    
    logger.info(f"Proxying {request.method} {path} to {target_url}")
    
    # Handle WebSocket upgrade
    if request.headers.get('Upgrade') == 'websocket':
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        # Connect to backend WebSocket
        session = aiohttp.ClientSession()
        try:
            async with session.ws_connect('ws://localhost:8080') as backend_ws:
                # Relay messages
                async def relay_to_backend():
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            await backend_ws.send_str(msg.data)
                        elif msg.type == aiohttp.WSMsgType.BINARY:
                            await backend_ws.send_bytes(msg.data)
                        else:
                            break
                
                async def relay_to_client():
                    async for msg in backend_ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            await ws.send_str(msg.data)
                        elif msg.type == aiohttp.WSMsgType.BINARY:
                            await ws.send_bytes(msg.data)
                        else:
                            break
                
                # Run both relay tasks
                import asyncio
                await asyncio.gather(relay_to_backend(), relay_to_client())
        finally:
            await session.close()
        
        return ws
    
    # Handle regular HTTP requests
    async with aiohttp.ClientSession() as session:
        # Forward the request
        data = await request.read() if request.body_exists else None
        
        async with session.request(
            method=request.method,
            url=target_url,
            headers=request.headers,
            data=data
        ) as response:
            body = await response.read()
            return web.Response(
                body=body,
                status=response.status,
                headers=response.headers
            )

async def create_app():
    app = web.Application()
    app.router.add_route('*', '/{path:.*}', handle_proxy)
    return app

if __name__ == '__main__':
    app = create_app()
    logger.info("Starting proxy server on port 8000")
    web.run_app(app, host='0.0.0.0', port=8000)
