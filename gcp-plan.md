# GCP Firebase Frontend Deployment Plan

## Overview
Deploy the frontend to Firebase Hosting and connect it to the Google Cloud Run backend service for full production deployment according to plan.md iteration 11.

## Current Status
- ✅ **Backend**: Successfully deployed to Cloud Run at `https://hybrid-stt-service-ysw2dobxea-ew.a.run.app`
- ✅ **WebSocket Endpoints**: `/ws/speak/{stream_id}` and `/ws/listen/{stream_id}` operational
- ❌ **Frontend**: Currently uses localhost configuration, needs Firebase deployment

## Deployment Plan

### Phase 1: TDD Tests for Frontend Integration
**Objective**: Ensure frontend works with Cloud Run backend using Test-Driven Development

#### Test 1.1: Cloud Run Configuration Test
```javascript
// Test that frontend config correctly uses production URL
describe('Cloud Run Integration', () => {
  test('should use production WebSocket URL in production', () => {
    const config = require('../src/config');
    process.env.NODE_ENV = 'production';
    const wsUrl = config.getWebSocketURL();
    expect(wsUrl).toBe('wss://hybrid-stt-service-ysw2dobxea-ew.a.run.app');
  });
});
```

#### Test 1.2: WebSocket Connection Test
```javascript
// Test WebSocket connection to Cloud Run
test('should connect to Cloud Run WebSocket endpoints', async () => {
  const ws = new WebSocket('wss://hybrid-stt-service-ysw2dobxea-ew.a.run.app/ws/speak/test-stream');
  await new Promise((resolve) => {
    ws.onopen = resolve;
  });
  expect(ws.readyState).toBe(WebSocket.OPEN);
});
```

### Phase 2: Frontend Configuration Update
**Objective**: Update frontend to work with production Cloud Run backend

#### Step 2.1: Update Configuration
- Update `frontend/src/config.js` production WebSocket URL
- Configure CORS headers if needed
- Set up environment-specific configurations

#### Step 2.2: Test Local Frontend with Cloud Run Backend
- Update local frontend to point to Cloud Run
- Test speaker/listener functionality locally before deployment

### Phase 3: Firebase Hosting Setup
**Objective**: Configure Firebase Hosting for static site deployment

#### Step 3.1: Firebase Initialization
```bash
cd frontend
npm install -g firebase-tools
firebase login
firebase init hosting
```

#### Step 3.2: Firebase Configuration
Create `firebase.json`:
```json
{
  "hosting": {
    "public": "dist",
    "ignore": ["firebase.json", "**/.*", "**/node_modules/**"],
    "rewrites": [{
      "source": "**",
      "destination": "/index.html"
    }],
    "headers": [{
      "source": "**/*.@(js|css)",
      "headers": [{
        "key": "Cache-Control",
        "value": "max-age=31536000"
      }]
    }]
  }
}
```

#### Step 3.3: Build Process
```bash
npm run build    # Build production assets
firebase deploy  # Deploy to Firebase
```

### Phase 4: Production Testing
**Objective**: End-to-end testing of complete system

#### Test 4.1: Speaker/Listener Flow
1. Open Firebase hosted frontend
2. Test speaker mode (Dutch → English translation)
3. Test listener mode (receive English audio)
4. Test multiple listeners on same stream

#### Test 4.2: Performance Validation
- Measure end-to-end latency
- Test connection stability
- Validate audio quality
- Monitor error rates

### Phase 5: Monitoring & Optimization
**Objective**: Production monitoring and performance optimization

#### Step 5.1: Monitoring Setup
- Firebase Performance Monitoring
- Google Analytics (optional)
- Error tracking with Firebase Crashlytics

#### Step 5.2: CDN & Caching
- Configure Firebase CDN settings
- Optimize asset delivery
- Set appropriate cache headers

## Implementation Steps

### 1. Write TDD Tests First
```bash
# Frontend tests for Cloud Run integration
npm test tests/cloud-run-integration.test.js
```

### 2. Update Frontend Configuration
```bash
# Update config to use Cloud Run URL
vim frontend/src/config.js
```

### 3. Local Testing with Cloud Run
```bash
# Test locally with production backend
npm run serve
# Test in browser: http://localhost:3000
```

### 4. Firebase Setup
```bash
cd frontend
firebase init hosting
# Configure build directory, rewrites, etc.
```

### 5. Build and Deploy
```bash
npm run build
firebase deploy
```

### 6. Production Testing
```bash
# Test complete system
curl https://your-app.firebaseapp.com/health
```

## File Structure After Deployment
```
frontend/
├── dist/                 # Built assets for deployment
├── firebase.json         # Firebase hosting configuration
├── .firebaserc          # Firebase project configuration
├── src/
│   ├── config.js        # Updated with Cloud Run URL
│   ├── connection.js    # WebSocket management
│   ├── audio.js         # Audio handling
│   └── ui.js           # UI management
├── tests/
│   ├── cloud-run-integration.test.js  # New integration tests
│   └── firebase-deployment.test.js    # Deployment tests
└── package.json         # Updated with Firebase dependencies
```

## Expected URLs After Deployment
- **Frontend**: `https://your-project.firebaseapp.com`
- **Backend**: `https://hybrid-stt-service-ysw2dobxea-ew.a.run.app`
- **WebSocket Speaker**: `wss://hybrid-stt-service-ysw2dobxea-ew.a.run.app/ws/speak/{stream_id}`
- **WebSocket Listener**: `wss://hybrid-stt-service-ysw2dobxea-ew.a.run.app/ws/listen/{stream_id}`

## Success Criteria
1. ✅ Frontend deployed to Firebase Hosting
2. ✅ WebSocket connections work from Firebase to Cloud Run
3. ✅ Speaker mode: Dutch audio → English translation
4. ✅ Listener mode: Receive translated audio
5. ✅ Multi-listener support on same stream
6. ✅ End-to-end latency < 3 seconds
7. ✅ Error handling and recovery mechanisms working
8. ✅ Production monitoring in place

## Risk Mitigation
- **CORS Issues**: Configure Cloud Run CORS if needed
- **WebSocket Timeouts**: Implement reconnection logic
- **Audio Codec Issues**: Test multiple browser audio formats
- **Performance**: Monitor and optimize based on real usage
- **Security**: Validate input sanitization and rate limiting