#!/usr/bin/env python3
"""
Standalone Monitoring Server for Twilio RIVA Voice Agent
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add the project directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from monitoring import MonitoringServer
from performance_optimizer import PerformanceOptimizer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Main entry point for monitoring server"""
    try:
        # Initialize performance optimizer
        performance_optimizer = PerformanceOptimizer()
        
        # Initialize and start monitoring server
        monitoring_server = MonitoringServer(performance_optimizer)
        await monitoring_server.start()
        
        logger.info("Monitoring server is running...")
        
        # Keep the server running
        while True:
            await asyncio.sleep(3600)  # Sleep for an hour
            
    except KeyboardInterrupt:
        logger.info("Monitoring server stopped by user")
    except Exception as e:
        logger.error(f"Error in monitoring server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
