#!/bin/bash
# Extended Streaming Test Runner
# 
# This script runs the 15-minute streaming test to validate
# the 5-minute stream restart logic works correctly.

set -e

echo "🚀 Extended Streaming Test - 5-minute restart validation"
echo "========================================================"

# Check if backend is running
echo "🔍 Checking backend status..."
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "❌ Backend not running. Starting backend..."
    poetry run uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
    BACKEND_PID=$!
    echo "⏳ Waiting for backend to start..."
    sleep 5
    
    # Verify backend started
    if ! curl -s http://localhost:8000/health > /dev/null; then
        echo "❌ Failed to start backend"
        exit 1
    fi
    echo "✅ Backend started successfully"
else
    echo "✅ Backend is already running"
    BACKEND_PID=""
fi

# Install test dependencies using poetry (websockets already in main deps)
echo "📦 Installing test dependencies with poetry..."
poetry add numpy aiohttp --group dev

# Run the extended streaming test with poetry
echo "🎬 Starting 15-minute streaming test..."
echo "   This will test the 5-minute stream restart logic"
echo "   Expected behavior: Stream restarts at 4:40, 9:20, 14:00"
echo ""

poetry run python test_extended_streaming.py

TEST_EXIT_CODE=$?

# Cleanup
if [ -n "$BACKEND_PID" ]; then
    echo "🧹 Stopping backend..."
    kill $BACKEND_PID 2>/dev/null || true
fi

# Report results
echo ""
echo "========================================================"
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ EXTENDED STREAMING TEST PASSED"
    echo "   - Stream restart logic working correctly"
    echo "   - No data loss detected"
    echo "   - Transcript continuity maintained"
    echo "   - Error rate within acceptable limits"
else
    echo "❌ EXTENDED STREAMING TEST FAILED"
    echo "   Check the test logs for detailed failure analysis"
fi
echo "========================================================"

exit $TEST_EXIT_CODE