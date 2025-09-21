#!/bin/bash
#
# Stop script for Twilio RIVA Voice Agent Service
#

# Configuration
BASE_DIR="/home/ubuntu/twilio_riva_agent"
PID_DIR="$BASE_DIR/pids"
LOG_DIR="$BASE_DIR/logs"

# Function to stop a component
stop_component() {
    local name=$1
    local pid_file="$PID_DIR/${name}.pid"
    
    if [ -f "$pid_file" ]; then
        pid=$(cat "$pid_file")
        if kill -0 $pid 2>/dev/null; then
            echo "Stopping $name (PID: $pid)..."
            kill $pid
            
            # Wait for graceful shutdown
            for i in {1..10}; do
                if ! kill -0 $pid 2>/dev/null; then
                    echo "$name stopped successfully"
                    rm -f "$pid_file"
                    return 0
                fi
                sleep 1
            done
            
            # Force kill if still running
            echo "Force stopping $name..."
            kill -9 $pid 2>/dev/null
            rm -f "$pid_file"
        else
            echo "$name is not running (stale PID file)"
            rm -f "$pid_file"
        fi
    else
        echo "$name is not running (no PID file)"
    fi
}

echo "Stopping Twilio RIVA Voice Agent services..."

# Stop all services in reverse order
stop_component "dashboard"
stop_component "websocket"
stop_component "twiml"
stop_component "monitoring"
stop_component "ngrok_monitor"
stop_component "ngrok_twiml"
stop_component "ngrok_ws"

# Update status file
if [ -f "$BASE_DIR/service_status.json" ]; then
    cat > "$BASE_DIR/service_status.json" << STATUS
{
    "status": "stopped",
    "stopped_at": "$(date -Iseconds)",
    "services": {}
}
STATUS
fi

echo "All services stopped"
exit 0
