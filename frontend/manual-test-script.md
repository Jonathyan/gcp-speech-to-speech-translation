# Manual Testing Script

## Prerequisites
1. Backend server running: `poetry run uvicorn gcp_speech_to_speech_translation.main:app --reload`
2. Frontend served: `npm run serve` or open `public/index.html`

## Test Scenarios

### 1. Basic Connection Test
**Steps:**
1. Open `public/index.html` in browser
2. Open browser console (F12)
3. Click "Start Uitzending"
4. Observe status changes and console logs

**Expected Results:**
- Status: "Verbinden..." → "Verbonden - Klaar om uit te zenden"
- No JavaScript errors in console
- Disconnect button becomes enabled

### 2. Error Handling Test
**Steps:**
1. Ensure backend is NOT running
2. Click "Start Uitzending"
3. Wait for retry attempts (2s, 4s, 8s)
4. Observe final error message

**Expected Results:**
- Status shows retry attempts with countdown
- Final status: "Verbinding mislukt - Controleer of de server draait"
- Buttons re-enable after failure

### 3. Listener Mode Test
**Steps:**
1. Start backend server
2. Click "Luister mee"
3. Observe different status messages

**Expected Results:**
- Status: "Verbinden als luisteraar..." → "Verbonden - Luisteren..."
- Connection successful with listener-specific messaging

### 4. Disconnect Test
**Steps:**
1. Connect successfully (either mode)
2. Click "Verbinding Verbreken"
3. Observe clean disconnection

**Expected Results:**
- Status: "Verbinding gesloten"
- All buttons return to initial state
- No errors in console

### 5. Cross-Browser Test
**Browsers to test:**
- Chrome/Chromium
- Firefox
- Safari (macOS)
- Edge (if available)

**Expected Results:**
- Consistent behavior across browsers
- WebSocket support detection
- Responsive design works on mobile

### 6. Network Scenarios
**Test offline behavior:**
1. Connect successfully
2. Disconnect network (airplane mode)
3. Observe connection loss handling

**Test slow connection:**
1. Use browser dev tools to throttle network
2. Attempt connection
3. Verify timeout handling

## Performance Checklist
- [ ] Page loads quickly (< 1s)
- [ ] Button clicks are responsive
- [ ] Status updates are immediate
- [ ] No memory leaks during reconnections
- [ ] Smooth animations/transitions

## Browser Console Commands
```javascript
// Test functions directly
startBroadcast();
joinListener();
updateStatus('Test message');
disconnectWebSocket();

// Check WebSocket state
console.log(currentWebSocket);
```

## Common Issues & Solutions
- **WebSocket connection refused**: Check backend is running on port 8000
- **CORS errors**: Ensure backend allows frontend origin
- **Buttons not responding**: Check console for JavaScript errors
- **Status not updating**: Verify DOM elements exist