#!/usr/bin/env python3
"""
Load Testing Script for Twilio RIVA Voice Agent
Tests system performance under various load conditions
"""

import asyncio
import aiohttp
import json
import time
import random
import statistics
from typing import List, Dict, Any
from datetime import datetime
import argparse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LoadTester:
    """Load testing for the voice agent system"""
    
    def __init__(self, base_url: str, twilio_phone: str):
        self.base_url = base_url
        self.twilio_phone = twilio_phone
        self.results = []
        self.errors = []
        
    async def simulate_call(self, call_id: str, duration: int = 60):
        """Simulate a single call"""
        start_time = time.time()
        result = {
            'call_id': call_id,
            'start_time': start_time,
            'duration': 0,
            'latencies': [],
            'errors': [],
            'success': False
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                # Simulate call initiation
                async with session.post(
                    f"{self.base_url}/test/initiate_call",
                    json={
                        'call_id': call_id,
                        'from': f"+1234567890{call_id[-4:]}",
                        'to': self.twilio_phone
                    }
                ) as resp:
                    if resp.status != 200:
                        result['errors'].append(f"Failed to initiate call: {resp.status}")
                        return result
                
                # Simulate conversation interactions
                interactions = duration // 10  # One interaction every 10 seconds
                for i in range(interactions):
                    interaction_start = time.time()
                    
                    # Simulate ASR
                    await self._simulate_asr(session, call_id)
                    
                    # Simulate LLM processing
                    await self._simulate_llm(session, call_id)
                    
                    # Simulate TTS
                    await self._simulate_tts(session, call_id)
                    
                    interaction_latency = (time.time() - interaction_start) * 1000
                    result['latencies'].append(interaction_latency)
                    
                    # Wait before next interaction
                    await asyncio.sleep(random.uniform(8, 12))
                
                # Simulate call completion
                async with session.post(
                    f"{self.base_url}/test/complete_call",
                    json={'call_id': call_id}
                ) as resp:
                    if resp.status == 200:
                        result['success'] = True
                        
        except Exception as e:
            result['errors'].append(str(e))
            logger.error(f"Error in call {call_id}: {e}")
            
        result['duration'] = time.time() - start_time
        return result
        
    async def _simulate_asr(self, session: aiohttp.ClientSession, call_id: str):
        """Simulate ASR processing"""
        # Generate random audio duration (simulating speech)
        audio_duration = random.uniform(2, 5)
        await asyncio.sleep(audio_duration * 0.1)  # Simulate processing time
        
    async def _simulate_llm(self, session: aiohttp.ClientSession, call_id: str):
        """Simulate LLM processing"""
        # Simulate LLM thinking time
        await asyncio.sleep(random.uniform(0.5, 2))
        
    async def _simulate_tts(self, session: aiohttp.ClientSession, call_id: str):
        """Simulate TTS processing"""
        # Simulate TTS generation time
        await asyncio.sleep(random.uniform(0.3, 1))
        
    async def run_concurrent_calls(self, num_calls: int, duration: int = 60):
        """Run multiple concurrent calls"""
        logger.info(f"Starting {num_calls} concurrent calls for {duration} seconds each")
        
        tasks = []
        for i in range(num_calls):
            call_id = f"test_{int(time.time())}_{i:04d}"
            task = asyncio.create_task(self.simulate_call(call_id, duration))
            tasks.append(task)
            
            # Stagger call starts slightly
            await asyncio.sleep(random.uniform(0.1, 0.5))
        
        # Wait for all calls to complete
        results = await asyncio.gather(*tasks)
        self.results.extend(results)
        
        logger.info(f"Completed {num_calls} calls")
        
    async def run_ramp_up_test(self, max_calls: int, duration: int = 60, ramp_time: int = 30):
        """Gradually increase load"""
        logger.info(f"Starting ramp-up test to {max_calls} calls over {ramp_time} seconds")
        
        calls_per_interval = max_calls // (ramp_time // 5)
        current_calls = 0
        
        for i in range(ramp_time // 5):
            new_calls = min(calls_per_interval, max_calls - current_calls)
            logger.info(f"Adding {new_calls} calls (total: {current_calls + new_calls})")
            
            tasks = []
            for j in range(new_calls):
                call_id = f"ramp_{int(time.time())}_{current_calls + j:04d}"
                task = asyncio.create_task(self.simulate_call(call_id, duration))
                tasks.append(task)
                
            current_calls += new_calls
            await asyncio.sleep(5)
            
        # Wait for all calls to complete
        logger.info("Waiting for all calls to complete...")
        await asyncio.sleep(duration)
        
    async def run_spike_test(self, spike_calls: int, normal_calls: int = 5):
        """Test system response to sudden load spikes"""
        logger.info(f"Starting spike test: normal={normal_calls}, spike={spike_calls}")
        
        # Run normal load
        await self.run_concurrent_calls(normal_calls, 30)
        
        # Create sudden spike
        logger.info(f"Creating load spike with {spike_calls} calls")
        await self.run_concurrent_calls(spike_calls, 30)
        
        # Return to normal
        logger.info("Returning to normal load")
        await self.run_concurrent_calls(normal_calls, 30)
        
    async def run_endurance_test(self, num_calls: int, duration: int = 3600):
        """Long-running test for stability"""
        logger.info(f"Starting endurance test: {num_calls} calls for {duration} seconds")
        
        start_time = time.time()
        batch_num = 0
        
        while time.time() - start_time < duration:
            batch_num += 1
            logger.info(f"Starting batch {batch_num}")
            
            await self.run_concurrent_calls(num_calls, min(60, duration - (time.time() - start_time)))
            
            # Short break between batches
            await asyncio.sleep(5)
            
    def analyze_results(self) -> Dict[str, Any]:
        """Analyze test results"""
        if not self.results:
            return {"error": "No results to analyze"}
            
        successful_calls = [r for r in self.results if r['success']]
        failed_calls = [r for r in self.results if not r['success']]
        
        all_latencies = []
        for result in successful_calls:
            all_latencies.extend(result['latencies'])
            
        analysis = {
            'summary': {
                'total_calls': len(self.results),
                'successful_calls': len(successful_calls),
                'failed_calls': len(failed_calls),
                'success_rate': len(successful_calls) / len(self.results) if self.results else 0
            }
        }
        
        if all_latencies:
            analysis['latency'] = {
                'mean': statistics.mean(all_latencies),
                'median': statistics.median(all_latencies),
                'stdev': statistics.stdev(all_latencies) if len(all_latencies) > 1 else 0,
                'min': min(all_latencies),
                'max': max(all_latencies),
                'p50': self._percentile(all_latencies, 50),
                'p95': self._percentile(all_latencies, 95),
                'p99': self._percentile(all_latencies, 99)
            }
            
        if successful_calls:
            durations = [r['duration'] for r in successful_calls]
            analysis['call_duration'] = {
                'mean': statistics.mean(durations),
                'median': statistics.median(durations),
                'min': min(durations),
                'max': max(durations)
            }
            
        if failed_calls:
            error_types = {}
            for call in failed_calls:
                for error in call['errors']:
                    error_type = error.split(':')[0] if ':' in error else error
                    error_types[error_type] = error_types.get(error_type, 0) + 1
            analysis['errors'] = error_types
            
        return analysis
        
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile"""
        sorted_data = sorted(data)
        index = (len(sorted_data) - 1) * percentile / 100
        lower = int(index)
        upper = lower + 1
        if upper >= len(sorted_data):
            return sorted_data[lower]
        return sorted_data[lower] + (sorted_data[upper] - sorted_data[lower]) * (index - lower)
        
    def print_report(self):
        """Print test report"""
        analysis = self.analyze_results()
        
        print("\n" + "="*60)
        print("LOAD TEST RESULTS")
        print("="*60)
        
        if 'error' in analysis:
            print(f"Error: {analysis['error']}")
            return
            
        # Summary
        print("\nSUMMARY:")
        print("-"*30)
        for key, value in analysis['summary'].items():
            if isinstance(value, float):
                print(f"  {key}: {value:.2f}")
            else:
                print(f"  {key}: {value}")
                
        # Latency stats
        if 'latency' in analysis:
            print("\nLATENCY (ms):")
            print("-"*30)
            for key, value in analysis['latency'].items():
                print(f"  {key}: {value:.2f}")
                
        # Call duration
        if 'call_duration' in analysis:
            print("\nCALL DURATION (seconds):")
            print("-"*30)
            for key, value in analysis['call_duration'].items():
                print(f"  {key}: {value:.2f}")
                
        # Errors
        if 'errors' in analysis:
            print("\nERRORS:")
            print("-"*30)
            for error_type, count in analysis['errors'].items():
                print(f"  {error_type}: {count}")
                
        print("\n" + "="*60)
        
    def save_results(self, filename: str = None):
        """Save results to file"""
        if filename is None:
            filename = f"load_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
        analysis = self.analyze_results()
        data = {
            'timestamp': datetime.now().isoformat(),
            'analysis': analysis,
            'raw_results': self.results
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
            
        logger.info(f"Results saved to {filename}")

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Load test the voice agent system')
    parser.add_argument('--base-url', default='http://localhost:8080', help='Base URL for the system')
    parser.add_argument('--twilio-phone', default='+1234567890', help='Twilio phone number')
    parser.add_argument('--test-type', choices=['concurrent', 'ramp', 'spike', 'endurance'], 
                       default='concurrent', help='Type of load test')
    parser.add_argument('--calls', type=int, default=10, help='Number of concurrent calls')
    parser.add_argument('--duration', type=int, default=60, help='Duration of each call in seconds')
    parser.add_argument('--output', help='Output file for results')
    
    args = parser.parse_args()
    
    # For actual testing against real system, use monitoring endpoint
    if args.base_url == 'http://localhost:8080':
        # Use monitoring server endpoint for testing
        args.base_url = 'http://localhost:9090'
    
    tester = LoadTester(args.base_url, args.twilio_phone)
    
    try:
        if args.test_type == 'concurrent':
            await tester.run_concurrent_calls(args.calls, args.duration)
        elif args.test_type == 'ramp':
            await tester.run_ramp_up_test(args.calls, args.duration)
        elif args.test_type == 'spike':
            await tester.run_spike_test(args.calls)
        elif args.test_type == 'endurance':
            await tester.run_endurance_test(args.calls, args.duration)
            
        # Print and save results
        tester.print_report()
        
        if args.output:
            tester.save_results(args.output)
        else:
            tester.save_results()
            
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        tester.print_report()
        
if __name__ == "__main__":
    asyncio.run(main())
