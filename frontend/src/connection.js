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

// Audio player integration
let audioPlayer = null;
let audioStats = {
  chunksReceived: 0,
  bytesReceived: 0,
  chunksProcessed: 0,
  processingErrors: 0
};

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
  if (lastSendTime === 0 || now - lastSendTime > RATE_LIMIT_WINDOW) {
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
  
  // Initialize audio player for listener mode
  if (mode === 'listener') {
    initializeAudioPlayer();
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
  audioStats.chunksReceived++;
  audioStats.bytesReceived += audioData.byteLength;
  
  console.log('Audio data received:', audioData.byteLength, 'bytes');
  
  if (!audioPlayer) {
    console.warn('AudioPlayer not initialized - audio data ignored');
    return;
  }
  
  // Process audio data asynchronously
  processAudioData(audioData);
}

/**
 * Process audio data for playback
 * @param {ArrayBuffer} audioData - Binary audio data
 */
async function processAudioData(audioData) {
  try {
    // Decode audio chunk
    const audioBuffer = await audioPlayer.decodeAudioChunk(audioData);
    
    // Validate audio buffer
    const validation = audioPlayer.validateAudioBuffer(audioBuffer);
    if (!validation.valid) {
      console.error('Invalid audio buffer:', validation.errors);
      audioStats.processingErrors++;
      return;
    }
    
    // Add to playback queue
    const added = audioPlayer.addToQueue(audioBuffer);
    if (added) {
      audioStats.chunksProcessed++;
      console.log('Audio chunk queued for playback');
    } else {
      console.warn('Failed to add audio chunk to queue');
      audioStats.processingErrors++;
    }
    
  } catch (error) {
    console.error('Audio processing error:', error);
    audioStats.processingErrors++;
  }
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
  try {
    // Try to parse as JSON for control messages
    const message = JSON.parse(data);
    console.log('Control message received:', message);
    
    // Handle different message types
    if (message.type === 'audio_start') {
      handleAudioStreamStart();
    } else if (message.type === 'audio_end') {
      handleAudioStreamEnd();
    } else if (message.type === 'error') {
      console.error('Server error:', message.error);
    }
    
  } catch (error) {
    // Not JSON, treat as plain text message
    console.log('Text message received:', data);
  }
}

/**
 * Handle audio stream start
 */
function handleAudioStreamStart() {
  if (audioPlayer && !audioPlayer.isStreaming) {
    audioPlayer.startStreamPlayback();
    console.log('Audio stream playback started');
  }
}

/**
 * Handle audio stream end
 */
function handleAudioStreamEnd() {
  if (audioPlayer && audioPlayer.isStreaming) {
    // Let current queue finish playing
    setTimeout(() => {
      if (audioPlayer.getQueueSize() === 0) {
        audioPlayer.stopStreamPlayback();
        console.log('Audio stream playback stopped');
      }
    }, 1000);
  }
}

/**
 * Initialize audio player for listener mode
 */
function initializeAudioPlayer() {
  try {
    if (typeof AudioPlayer !== 'undefined') {
      audioPlayer = new AudioPlayer();
      audioPlayer.createAudioContext();
      
      // Reset audio statistics
      audioStats = {
        chunksReceived: 0,
        bytesReceived: 0,
        chunksProcessed: 0,
        processingErrors: 0
      };
      
      console.log('AudioPlayer initialized for listener mode');
    } else {
      console.error('AudioPlayer class not available');
    }
  } catch (error) {
    console.error('Failed to initialize AudioPlayer:', error);
  }
}

/**
 * Cleanup audio player
 */
function cleanupAudioPlayer() {
  if (audioPlayer) {
    audioPlayer.stopStreamPlayback();
    audioPlayer.clearQueue();
    audioPlayer = null;
    console.log('AudioPlayer cleaned up');
  }
}

/**
 * Get audio statistics
 * @returns {object} Audio processing statistics
 */
function getAudioStats() {
  return { ...audioStats };
}

/**
 * Disconnect WebSocket cleanly
 */
function disconnectWebSocket() {
  if (currentWebSocket) {
    currentWebSocket.close();
    currentWebSocket = null;
  }
  
  // Cleanup audio player
  cleanupAudioPlayer();
  
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
    getCurrentWebSocket,
    getAudioStats,
    initializeAudioPlayer,
    cleanupAudioPlayer
  };
}

if (typeof window !== 'undefined') {
  window.AppConnection = { 
    connectWebSocket, 
    disconnectWebSocket, 
    sendAudioChunk,
    generateStreamId,
    getCurrentWebSocket,
    getAudioStats,
    initializeAudioPlayer,
    cleanupAudioPlayer
  };
}