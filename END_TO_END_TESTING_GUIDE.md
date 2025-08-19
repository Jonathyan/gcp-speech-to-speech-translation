# End-to-End Testing Guide

## 🎯 Testing the Complete Dutch-to-English Translation Pipeline

This guide will help you test the complete speech-to-speech translation system with all Phase 1 optimizations.

## Prerequisites Setup

### 1. Google Cloud Credentials
```bash
# Set the credentials environment variable
export GOOGLE_APPLICATION_CREDENTIALS="credentials/service-account.json"

# Verify credentials are valid
gcloud auth application-default print-access-token
```

### 2. Backend Service
```bash
# Start the optimized backend
poetry run uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Verify health in another terminal
curl http://localhost:8000/health | jq .
# Should show: "translation": "connected", "tts": "connected"
```

### 3. Frontend Service
```bash
# In frontend directory
cd frontend
npm run serve
# Frontend available at http://localhost:3000
```

## 🧪 Testing Methods

### Method 1: Browser-Based Testing (Recommended)

**Step 1: Start Broadcasting**
1. Open http://localhost:3000
2. Click "Start Uitzending" (Start Broadcasting)
3. Allow microphone access when prompted
4. You should see: "🎙️ Stream started" in backend logs

**Step 2: Start Listening**  
1. Open a new browser tab/window to http://localhost:3000
2. Click "Luister mee" (Listen along)
3. Enter stream ID (or use default)
4. You should see: "🎧 Listener joined" in backend logs

**Step 3: Test Translation**
1. In the broadcasting tab, speak Dutch into the microphone:
   - "Hallo, dit is een test" (Hello, this is a test)
   - "Hoe gaat het vandaag?" (How are you today?)
   - "Het weer is vandaag heel mooi" (The weather is very nice today)

2. Expected flow in backend logs:
   ```
   📝 Final transcript: 'hallo dit is een test'
   📝 Translation: 'hello this is a test'
   🔊 Audio broadcast: 1234 bytes
   ```

3. Expected result in listening tab:
   - English audio should play automatically
   - Should hear synthesized English speech

### Method 2: WebSocket Testing Script

I'll create a test script that simulates the browser behavior: