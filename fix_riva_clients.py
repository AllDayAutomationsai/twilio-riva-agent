#!/usr/bin/env python3
"""Fix RIVA client initialization for new API"""

import fileinput
import sys

def fix_asr_client():
    file_path = "/home/ubuntu/twilio_riva_agent/services/riva_asr_client.py"
    
    # Read the file
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Fix the initialization
    with open(file_path, 'w') as f:
        for i, line in enumerate(lines):
            if "self.auth = None  # No auth needed for local RIVA" in line:
                # Replace with proper Auth initialization
                f.write("            # Use the new RIVA client API\n")
                f.write("            self.auth = riva.client.Auth(uri=self.server)\n")
            elif "self.asr_service = riva.client.ASRService(self.auth, self.server)" in line:
                # Fix ASRService initialization (now only takes auth)
                f.write("            self.asr_service = riva.client.ASRService(self.auth)\n")
            else:
                f.write(line)
    
    print("Fixed riva_asr_client.py")

def fix_tts_client():
    file_path = "/home/ubuntu/twilio_riva_agent/services/riva_tts_client.py"
    
    # Read the file
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Fix the initialization
    with open(file_path, 'w') as f:
        for i, line in enumerate(lines):
            if "self.auth = None  # or None if no auth" in line:
                # Replace with proper Auth initialization
                f.write("            # Use the new RIVA client API\n")
                f.write("            self.auth = riva.client.Auth(uri=self.server)\n")
            elif "self.tts = riva.client.SpeechSynthesisService(self.auth, self.server)" in line:
                # Fix SpeechSynthesisService initialization (now only takes auth)
                f.write("            self.tts = riva.client.SpeechSynthesisService(self.auth)\n")
            else:
                f.write(line)
    
    print("Fixed riva_tts_client.py")

if __name__ == "__main__":
    fix_asr_client()
    fix_tts_client()
    print("\nRIVA client files have been updated for the new API!")
