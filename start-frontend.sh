#!/bin/bash
# Linux/Mac script to start UC10 frontend React server

echo "========================================"
echo "UC10 Frontend - React Dev Server"
echo "========================================"
echo ""

# Change to frontend directory
cd "$(dirname "$0")/frontend"

# Install dependencies if needed
echo "Installing Node.js dependencies..."
npm install

# Start React dev server
echo ""
echo "Starting React dev server on http://localhost:5173"
echo "Press Ctrl+C to stop"
echo ""

npm run dev
