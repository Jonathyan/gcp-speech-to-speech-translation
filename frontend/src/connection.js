/**
 * WebSocket Connection Management Module
 * Handles WebSocket connections, retries, and error handling
 */

// Global connection state
let currentWebSocket = null;
let retryCount = 0;
let lastSendTime = 0;
let sendCount = 0;
const RATE_LIMIT_WINDOW = 1000; // 1 second
const MAX_SENDS_PER_WINDOW = 10; // Max 10 sends per second

/**
 * Send audio chunk via WebSocket
 * @param {WebSocket} websocket - WebSocket connection
 * @param {ArrayBuffer} audioData - Binary audio data
 * @returns {object} Result with success status
 */
function sendAudioChunk(websocket, audioData) {
  // Check WebSocket state
  if (!websocket || websocket.readyState !== WebSocket.OPEN) {
    return {
      success: false,
      error: 'WebSocket not ready'
    };
  }
  
  // Rate limiting
  const now = Date.now();
  if (now - lastSendTime > RATE_LIMIT_WINDOW) {
    // Reset counter for new window
    sendCount = 0;
    lastSendTime = now;
  }
  
  if (sendCount >= MAX_SENDS_PER_WINDOW) {
    return {
      success: false,
      error: 'Rate limited'
    };
  }
  
  try {
    websocket.send(audioData);
    sendCount++;
    return {
      success: true
    };
  } catch (error) {
    console.error('Failed to send audio chunk:', error);
    return {
      success: false,
      error: 'Failed to send audio chunk'
    };
  }
}

/**
 * Generate stream ID
 * @returns {string} Unique stream identifier
 */
function generateStreamId() {
  return `stream-${Date.now()}`;
}

/**
 * Establish WebSocket connection with retry logic
 * @param {string} url - WebSocket URL
 * @param {string} mode - Connection mode ('broadcast' or 'listener')
 * @param {string} streamId - Optional stream ID
 */
function connectWebSocket(url, mode, streamId) {
  const config = window.AppConfig.CONFIG.CONNECTION;
  
  // Generate stream ID if not provided
  if (!streamId) {
    streamId = generateStreamId();
  }
  
  // Build endpoint URL based on mode
  let wsUrl;
  if (mode === 'broadcast') {
    wsUrl = `${url}/ws/speak/${streamId}`;
  } else if (mode === 'listener') {
    wsUrl = `${url}/ws/listen/${streamId}`;
  } else {
    wsUrl = url; // Fallback to original URL
  }
  
  // Clean up existing connection
  if (currentWebSocket) {
    currentWebSocket.close();
    currentWebSocket = null;
  }
  
  try {
    currentWebSocket = new WebSocket(wsUrl);
    
    currentWebSocket.onopen = function() {
      retryCount = 0;
      handleConnectionSuccess(mode);
    };
    
    currentWebSocket.onclose = function(event) {
      currentWebSocket = null;
      if (event.wasClean) {
        handleCleanDisconnect();
      } else {
        handleConnectionError(url, mode, streamId);
      }
    };
    
    currentWebSocket.onerror = function(error) {
      console.error('WebSocket error during streaming:', error);
      handleConnectionError(url, mode, streamId);
    };
    
    currentWebSocket.onmessage = function(event) {
      // Handle both text and binary messages
      if (event.data instanceof ArrayBuffer) {
        handleIncomingAudioData(event.data);
      } else {
        handleIncomingMessage(event.data);
      }
    };
    
  } catch (error) {
    console.error('Failed to create WebSocket connection:', error);
    handleConnectionError(url, mode, streamId);
  }
}

/**
 * Handle successful connection
 * @param {string} mode - Connection mode
 */
function handleConnectionSuccess(mode) {
  const message = mode === 'broadcast' 
    ? 'Verbonden - Klaar om uit te zenden'
    : 'Verbonden - Luisteren...';
  
  window.AppUI.updateStatus(message);
  window.AppUI.enableButtons(false);
}

/**
 * Handle clean disconnection
 */
function handleCleanDisconnect() {
  window.AppUI.updateStatus('Verbinding gesloten');
  window.AppUI.enableButtons(true);
}

/**
 * Handle incoming binary audio data
 * @param {ArrayBuffer} audioData - Binary audio data
 */
function handleIncomingAudioData(audioData) {
  console.log('Audio data received:', audioData.byteLength, 'bytes');
  // Future: Process audio data for playback
}

/**
 * Handle connection errors with retry logic
 * @param {string} url - WebSocket URL
 * @param {string} mode - Connection mode
 * @param {string} streamId - Stream identifier
 */
function handleConnectionError(url, mode, streamId) {
  const config = window.AppConfig.CONFIG.CONNECTION;
  
  if (retryCount < config.maxRetries) {
    retryCount++;
    const delay = Math.pow(2, retryCount) * config.retryDelayBase;
    
    window.AppUI.updateStatus(`Verbinding mislukt - Opnieuw proberen in ${delay/1000}s...`);
    
    setTimeout(() => {
      window.AppUI.updateStatus('Opnieuw verbinden...');
      connectWebSocket(url, mode, streamId);
    }, delay);
  } else {
    window.AppUI.updateStatus('Verbinding mislukt - Controleer of de server draait');
    retryCount = 0;
    window.AppUI.enableButtons(true);
  }
}

/**
 * Handle incoming WebSocket messages
 * @param {string} data - Message data
 */
function handleIncomingMessage(data) {
  console.log('Message received:', data);
  // Future: Handle audio data processing
}

/**
 * Disconnect WebSocket cleanly
 */
function disconnectWebSocket() {
  if (currentWebSocket) {
    currentWebSocket.close();
    currentWebSocket = null;
  }
  window.AppUI.enableButtons(true);
  window.AppUI.updateStatus('Ready');
}

/**
 * Get current WebSocket connection
 * @returns {WebSocket|null} Current WebSocket instance
 */
function getCurrentWebSocket() {
  return currentWebSocket;
}

// Export for modules and browser
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { 
    connectWebSocket, 
    disconnectWebSocket, 
    sendAudioChunk,
    generateStreamId,
    getCurrentWebSocket
  };
}

if (typeof window !== 'undefined') {
  window.AppConnection = { 
    connectWebSocket, 
    disconnectWebSocket, 
    sendAudioChunk,
    generateStreamId,
    getCurrentWebSocket
  };
}