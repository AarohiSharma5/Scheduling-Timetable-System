#!/bin/bash
# Quick start script with database seeding

echo "🚀 Starting Backend with Fresh Database..."
echo ""

# Check if running in backend directory
if [ ! -f "requirements.txt" ]; then
  echo "❌ Error: Please run this script from the backend/ directory"
  exit 1
fi

# Install dependencies (if needed)
if ! python3 -c "import flask" 2>/dev/null; then
  echo "📦 Installing dependencies..."
  pip install -r requirements.txt
fi

# Seed database
echo "📊 Initializing database with seed data..."
python3 seed.py

if [ $? -eq 0 ]; then
  echo "✅ Database seeded successfully!"
  echo ""
  echo "🎯 Starting Flask server on http://localhost:5000/api"
  echo ""
  export FLASK_ENV=development
  export DATABASE_URL="sqlite:///timetable.db"
  python3 -m flask run --port=5000
else
  echo "❌ Seeding failed. Check the error above."
  exit 1
fi
