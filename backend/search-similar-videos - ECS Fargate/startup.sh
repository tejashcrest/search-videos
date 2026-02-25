#!/bin/bash
set -e

echo "🚀 Starting Video Search Service..."
echo ""

# Run user seeding script
echo "🌱 Seeding DocumentDB users..."
python seed_users.py
echo ""

# Start the main application
echo "🎯 Starting FastAPI application..."
exec python -m uvicorn main:app --host 0.0.0.0 --port 8000
