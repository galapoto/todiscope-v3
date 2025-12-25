#!/bin/bash

# TodiScope v3 Development Startup Script
# Starts both backend and frontend with combined logs

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to kill process on a specific port
kill_port() {
    local port=$1
    local killed=false
    local pids=""
    
    # Try using lsof (most common on macOS and Linux)
    if command -v lsof >/dev/null 2>&1; then
        pids=$(lsof -ti:$port 2>/dev/null)
        if [ ! -z "$pids" ]; then
            for pid in $pids; do
                print_info "Killing process on port $port (PID: $pid)..."
                kill -9 $pid 2>/dev/null || true
                killed=true
            done
        fi
    # Try using fuser (Linux)
    elif command -v fuser >/dev/null 2>&1; then
        pids=$(fuser $port/tcp 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i ~ /^[0-9]+$/) print $i}')
        if [ ! -z "$pids" ]; then
            for pid in $pids; do
                print_info "Killing process on port $port (PID: $pid)..."
                kill -9 $pid 2>/dev/null || true
                killed=true
            done
        fi
    # Try using ss (Linux)
    elif command -v ss >/dev/null 2>&1; then
        pids=$(ss -lptn 'sport = :'$port 2>/dev/null | grep -oP 'pid=\K\d+' | sort -u)
        if [ ! -z "$pids" ]; then
            for pid in $pids; do
                print_info "Killing process on port $port (PID: $pid)..."
                kill -9 $pid 2>/dev/null || true
                killed=true
            done
        fi
    # Try using netstat (fallback)
    elif command -v netstat >/dev/null 2>&1; then
        pids=$(netstat -tlnp 2>/dev/null | grep ":$port " | awk '{print $7}' | cut -d'/' -f1 | grep -E '^[0-9]+$' | sort -u)
        if [ ! -z "$pids" ]; then
            for pid in $pids; do
                print_info "Killing process on port $port (PID: $pid)..."
                kill -9 $pid 2>/dev/null || true
                killed=true
            done
        fi
    fi
    
    if [ "$killed" = true ]; then
        sleep 1  # Give the process a moment to die
        print_success "Port $port is now free"
    else
        # Check if port is actually free (no process found)
        if command -v lsof >/dev/null 2>&1; then
            if [ -z "$(lsof -ti:$port 2>/dev/null)" ]; then
                print_info "Port $port is already free"
            fi
        else
            print_info "Port $port check completed"
        fi
    fi
}

# Cleanup function
cleanup() {
    echo ""
    print_info "Shutting down services..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
        wait $BACKEND_PID 2>/dev/null || true
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
        wait $FRONTEND_PID 2>/dev/null || true
    fi
	    # Clean up any remaining processes
	    pkill -f "uvicorn backend.app.main:app" 2>/dev/null || true
	    print_info "Services stopped."
	    exit 0
	}

# Trap Ctrl+C
trap cleanup SIGINT SIGTERM EXIT

# Kill any processes using ports 3400 and 8400
echo ""
print_info "Checking and freeing ports 3400 and 8400..."
kill_port 3400
kill_port 8400
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    print_info "Creating virtual environment..."
    python3 -m venv .venv
    print_success "Virtual environment created"
fi

# Activate virtual environment
print_info "Activating virtual environment..."
source .venv/bin/activate

# Install backend dependencies if needed
if [ ! -f "backend/.installed" ]; then
    print_info "Installing backend dependencies (this may take a moment)..."
    pip install -e backend > /dev/null 2>&1
    touch backend/.installed
    print_success "Backend dependencies installed"
fi

# Check if frontend node_modules exists
if [ ! -d "frontend/node_modules" ]; then
    print_info "Installing frontend dependencies (this may take a moment)..."
    cd frontend
    npm install > /dev/null 2>&1
    cd ..
    print_success "Frontend dependencies installed"
fi

# Start backend with prefixed output
print_info "Starting backend on port 8400..."
(
    cd "$SCRIPT_DIR"
    source .venv/bin/activate
    uvicorn backend.app.main:app --reload --port 8400 2>&1 | sed "s/^/${BLUE}[BACKEND]${NC} /"
) &
BACKEND_PID=$!

# Start frontend with prefixed output
print_info "Starting frontend on port 3400..."
(
    cd "$SCRIPT_DIR/frontend/web"
    npm run dev 2>&1 | sed "s/^/${CYAN}[FRONTEND]${NC} /"
) &
FRONTEND_PID=$!

# Give services a moment to start
sleep 3

# Check if processes are still running
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    print_error "Backend failed to start"
    cleanup
    exit 1
fi

if ! kill -0 $FRONTEND_PID 2>/dev/null; then
    print_error "Frontend failed to start"
    cleanup
    exit 1
fi

# Display startup info
echo ""
print_success "Services started successfully!"
echo ""
echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Backend:${NC}  http://localhost:8400"
echo -e "${GREEN}Frontend:${NC} http://localhost:3400"
echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}"
echo ""
print_info "Logs from both services will appear below:"
print_info "Press ${YELLOW}Ctrl+C${NC} to stop both services"
echo ""

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
