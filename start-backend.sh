#!/bin/bash
# Linux/Mac script to start UC10 backend FastAPI server

echo "========================================"
echo "UC10 Backend - FastAPI Server"
echo "========================================"
echo ""

# Change to backend directory
cd "$(dirname "$0")/backend"

# Install dependencies if needed
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Start FastAPI server
echo ""
echo "Starting FastAPI server on http://localhost:8000"
echo "Press Ctrl+C to stop"
echo ""

python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
