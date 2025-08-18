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
  } else if (mode === 'streaming') {
    wsUrl = `${url}/ws/stream/${streamId}`;
    console.log('🚀 Using new streaming endpoint for real-time translation');
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
      // Handle both text and binary messages (ArrayBuffer or Blob)
      if (event.data instanceof ArrayBuffer || event.data instanceof Blob) {
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
 * Generate test beep using Web Audio API
 * @param {number} frequency - Frequency in Hz (default 800Hz)
 * @param {number} duration - Duration in seconds (default 0.3s)
 * @returns {Promise<void>} Promise that resolves when beep is played
 */
async function playTestBeep(frequency = 800, duration = 0.3) {
  try {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    
    // Create oscillator for beep sound
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();
    
    // Configure oscillator
    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);
    
    oscillator.frequency.value = frequency;
    oscillator.type = 'sine';
    
    // Configure volume envelope (fade in/out to avoid clicks)
    gainNode.gain.setValueAtTime(0, audioContext.currentTime);
    gainNode.gain.linearRampToValueAtTime(0.3, audioContext.currentTime + 0.05);
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + duration);
    
    // Play beep
    oscillator.start(audioContext.currentTime);
    oscillator.stop(audioContext.currentTime + duration);
    
    console.log(`Test beep played: ${frequency}Hz for ${duration}s`);
    
    // Clean up after beep finishes
    setTimeout(() => {
      audioContext.close();
    }, (duration + 0.1) * 1000);
    
  } catch (error) {
    console.error('Failed to play test beep:', error);
  }
}

// Track if user has interacted (for autoplay policy)
let userHasInteracted = false;

// Enable audio after user interaction
function enableAudioPlayback() {
  if (!userHasInteracted) {
    userHasInteracted = true;
    console.log('Audio playback enabled after user interaction');
    
    // Create and resume AudioContext to satisfy browser autoplay policy
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    audioContext.resume().then(() => {
      console.log('AudioContext resumed successfully');
      audioContext.close();
    });
  }
}

// Set up user interaction detection
if (typeof window !== 'undefined') {
  ['click', 'touchstart', 'keydown'].forEach(event => {
    window.addEventListener(event, enableAudioPlayback, { once: true });
  });
}

/**
 * Process audio data for playback - simplified direct playback with fallback
 * @param {ArrayBuffer|Blob} audioData - Binary audio data
 */
async function processAudioData(audioData) {
  try {
    console.log('Processing audio data:', typeof audioData, audioData.constructor.name);
    
    // Convert to ArrayBuffer for analysis
    let dataBuffer;
    if (audioData instanceof ArrayBuffer) {
      dataBuffer = audioData;
    } else if (audioData instanceof Blob) {
      dataBuffer = await audioData.arrayBuffer();
    } else {
      console.error('Unknown audio data type:', typeof audioData);
      audioStats.processingErrors++;
      return;
    }
    
    // Check if this is a test audio marker (only for mock TTS)
    let isTestMarker = false;
    try {
      const textDecoder = new TextDecoder('utf-8', {fatal: true});
      const dataAsText = textDecoder.decode(dataBuffer);
      
      if (dataAsText.startsWith('TEST_AUDIO_BEEP_MARKER:')) {
        console.log('Test audio marker detected, playing audible beep');
        const translatedText = dataAsText.substring('TEST_AUDIO_BEEP_MARKER:'.length);
        console.log('Mock translated text:', translatedText);
        
        // Play a pleasant test beep to confirm the system is working
        await playTestBeep(800, 0.4);
        audioStats.chunksProcessed++;
        return;
      }
    } catch (decodeError) {
      // Decoding failed - this is binary MP3 data, not a text marker
      console.log(`Binary MP3 data detected (${dataBuffer.byteLength} bytes), proceeding with audio playback`);
      isTestMarker = false;
    }
    
    // Skip test marker check for binary data - proceed directly to MP3 playback
    if (dataBuffer.byteLength > 1000) { // Real MP3 files are typically larger
      console.log(`Processing large audio file: ${dataBuffer.byteLength} bytes - likely real MP3`);
    }
    
    // Handle regular audio data
    const audioBlob = new Blob([dataBuffer], { type: 'audio/mpeg' });
    const audioUrl = URL.createObjectURL(audioBlob);
    const audio = new Audio(audioUrl);
    
    let audioPlayed = false;
    
    audio.onloadeddata = () => {
      console.log('Audio loaded, starting playback');
      audioStats.chunksProcessed++;
    };
    
    audio.onerror = (error) => {
      console.error('MP3 playback failed:', error);
      console.log('Audio blob details:', audioBlob.type, audioBlob.size, 'bytes');
      audioStats.processingErrors++;
      URL.revokeObjectURL(audioUrl);
      
      // Only play beep for very small data that might be fallback audio
      if (!audioPlayed && dataBuffer.byteLength < 1000) {
        console.log('Small data size, playing fallback beep');
        playTestBeep(600, 0.2);
      } else {
        console.log('Large MP3 data failed to play - not using fallback beep');
      }
    };
    
    audio.onended = () => {
      URL.revokeObjectURL(audioUrl);
      console.log('Audio playback completed');
      audioPlayed = true;
    };
    
    // Play the audio with error handling
    try {
      console.log(`Attempting to play MP3 audio: ${dataBuffer.byteLength} bytes`);
      
      // Check if user has interacted (for autoplay policy)
      if (!userHasInteracted) {
        console.warn('User interaction required for audio playback');
        // Show UI prompt for user to click
        if (window.AppUI && window.AppUI.showError) {
          window.AppUI.showError(
            'Klik ergens om audio af te spelen',
            'Browser vereist gebruikersinteractie voor audio',
            { recoverable: true, clearTime: 5000 }
          );
        }
        // Store audio for later playback after user interaction
        return;
      }
      
      await audio.play();
      audioPlayed = true;
      console.log('MP3 playback started successfully');
    } catch (playError) {
      console.error('Audio play() failed:', playError.message, playError);
      console.log('Play error details:', playError.name, playError.code);
      audioStats.processingErrors++;
      URL.revokeObjectURL(audioUrl);
      
      // Handle autoplay policy error specifically
      if (playError.name === 'NotAllowedError') {
        userHasInteracted = false; // Reset flag
        console.warn('Autoplay blocked - user interaction required');
        if (window.AppUI && window.AppUI.showError) {
          window.AppUI.showError(
            'Klik om audio te activeren',
            'Browser blokkeert automatisch afspelen',
            { recoverable: true, clearTime: 5000 }
          );
        }
      } else if (!audioPlayed && dataBuffer.byteLength < 1000) {
        // Only use beep fallback for small/invalid data
        console.log('Using beep fallback for small data');
        await playTestBeep(600, 0.2);
      } else {
        console.log('Large MP3 failed - no beep fallback (likely real audio issue)');
      }
    }
    
  } catch (error) {
    console.error('Audio processing error, playing error beep:', error);
    audioStats.processingErrors++;
    
    // Play distinctive error beep (higher frequency)
    await playTestBeep(1200, 0.1);
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
    // Simplified initialization for direct audio playback
    audioPlayer = {
      initialized: true,
      playback: 'direct'
    };
    
    // Reset audio statistics
    audioStats = {
      chunksReceived: 0,
      bytesReceived: 0,
      chunksProcessed: 0,
      processingErrors: 0
    };
    
    console.log('Direct audio player initialized for listener mode');
  } catch (error) {
    console.error('Failed to initialize audio player:', error);
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