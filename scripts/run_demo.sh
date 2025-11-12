#!/bin/bash

# Demo script for helpdesk auto-triage system

set -e

echo "🎫 Helpdesk Auto-Triage System - Demo Setup"
echo "=========================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.9 or higher."
    exit 1
fi

echo "✅ Python found: $(python3 --version)"

# Check if dependencies are installed
echo ""
echo "📦 Checking dependencies..."
if ! python3 -c "import fastapi" &> /dev/null; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
else
    echo "✅ Dependencies already installed"
fi

# Check for .env file
if [ ! -f .env ]; then
    echo ""
    echo "⚠️  No .env file found. Creating from .env.example..."
    cp .env.example .env
    echo ""
    echo "❗ IMPORTANT: Edit .env and add your ANTHROPIC_API_KEY"
    echo "   Get your key from: https://console.anthropic.com/"
    echo ""
    read -p "Press Enter after you've added your API key to .env..."
fi

# Initialize database
echo ""
echo "🗄️  Initializing database..."
python3 -c "import asyncio; from backend.database import init_db; asyncio.run(init_db())" 2>/dev/null || true
echo "✅ Database initialized"

# Seed sample tickets
echo ""
echo "🌱 Seeding sample tickets..."
python3 scripts/seed_sample_tickets.py

echo ""
echo "=========================================="
echo "🚀 Demo Ready!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Start the backend server:"
echo "   python3 backend/main.py"
echo ""
echo "2. In another terminal, serve the frontend:"
echo "   cd frontend && python3 -m http.server 3000"
echo ""
echo "3. Open your browser:"
echo "   http://localhost:3000"
echo ""
echo "4. Try the demo flow:"
echo "   - View the pre-seeded tickets"
echo "   - Click on any ticket to see details"
echo "   - Click 'Auto-Triage This Ticket'"
echo "   - Review AI-generated priority, assignee, and reply"
echo "   - Create new tickets and triage them"
echo ""
echo "📚 API Documentation: http://localhost:8000/docs"
echo ""
